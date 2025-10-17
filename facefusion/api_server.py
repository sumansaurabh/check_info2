"""
FastAPI REST API server for FaceFusion
Provides OpenAPI-compliant endpoints for external service integration
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from facefusion.env_helper import load_env

load_env()

from facefusion import logger, state_manager, wording  # noqa: E402
from facefusion.api_job_store import (  # noqa: E402
	create_job,
	get_job,
	init_db,
	list_jobs,
	update_job_status
)
from facefusion.args import apply_args  # noqa: E402
from facefusion.core import common_pre_check, process_step, processors_pre_check  # noqa: E402
from facefusion.filesystem import is_image, is_video  # noqa: E402
from facefusion.jobs import job_helper, job_manager, job_runner  # noqa: E402
from facefusion.processors.core import get_processors_modules  # noqa: E402
from facefusion.types import Args  # noqa: E402

init_db()


# Pydantic models for request/response
class ProcessRequest(BaseModel):
	"""Request model for processing operations"""
	processors: List[str] = Field(default=["face_swapper"], description="List of processors to apply")
	execution_providers: List[str] = Field(default=["cpu"], description="Execution providers (cpu, cuda, etc.)")
	execution_thread_count: int = Field(default=1, ge=1, le=32, description="Number of execution threads")
	output_video_fps: Optional[float] = Field(default=None, description="Output video FPS")
	output_image_scale: int = Field(default=100, ge=10, le=400, description="Output image scale percentage")
	output_video_scale: int = Field(default=100, ge=10, le=400, description="Output video scale percentage")
	face_detector_model: str = Field(default="yoloface_8n", description="Face detector model")
	face_detector_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Face detection confidence threshold")


class JobStatus(BaseModel):
	"""Job status response"""
	job_id: str
	status: str
	output_path: Optional[str] = None
	error: Optional[str] = None


class HealthResponse(BaseModel):
	"""Health check response"""
	status: str
	version: str
	processors_available: List[str]


class ProcessorInfo(BaseModel):
	"""Processor information"""
	name: str
	available: bool


# Initialize FastAPI app
app = FastAPI(
	title="FaceFusion API",
	description="REST API for FaceFusion face processing operations",
	version="3.3.0",
	docs_url="/docs",
	redoc_url="/redoc",
	openapi_url="/openapi.json"
)

# CORS middleware for external access
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Configure this appropriately for production
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Upload/output directories
UPLOAD_DIR = Path(os.getenv("API_UPLOAD_DIR", ".api_uploads"))
OUTPUT_DIR = Path(os.getenv("API_OUTPUT_DIR", ".api_outputs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_file(upload_file: UploadFile) -> str:
	"""Save uploaded file and return path"""
	file_ext = Path(upload_file.filename).suffix
	file_id = str(uuid.uuid4())
	file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

	with open(file_path, "wb") as f:
		f.write(upload_file.file.read())

	return str(file_path)


def cleanup_file(file_path: str) -> None:
	"""Clean up temporary file"""
	try:
		if os.path.exists(file_path):
			os.remove(file_path)
	except Exception as e:
		logger.warn(f"Failed to cleanup file {file_path}: {e}", __name__)


SOURCE_REQUIRED_PROCESSORS = { "face_swapper" }


def processors_require_source(processors: List[str]) -> bool:
	return any(processor in SOURCE_REQUIRED_PROCESSORS for processor in processors)


def map_job_status(job: dict) -> JobStatus:
	return JobStatus(
		job_id=job.get("job_id"),
		status=job.get("status"),
		output_path=job.get("output_path"),
		error=job.get("error")
	)


def execute_job(job_id: str, job_type: str, step_args: Args, target_path: str, source_path: Optional[str]) -> None:
	"""Execute a queued job and maintain status lifecycle."""
	try:
		logger.init(state_manager.get_item('log_level'))
		logger.info(f"[FACEFUSION.API] Running {job_type} job {job_id}", __name__)
		update_job_status(job_id, "running")

		# Ensure jobs infrastructure is ready when running in background
		jobs_path = state_manager.get_item('jobs_path') or '.jobs'
		if not job_manager.init_jobs(jobs_path):
			update_job_status(job_id, "failed", error="Failed to initialize job system")
			return

		success = job_runner.run_job(job_id, process_step)
		if success:
			update_job_status(job_id, "completed", output_path=step_args.get('output_path'))
		else:
			update_job_status(job_id, "failed", error="Job processing failed")
	except Exception as exc:
		logger.error(f"Background job {job_id} failed: {exc}", __name__)
		update_job_status(job_id, "failed", error=str(exc))
	finally:
		cleanup_file(target_path)
		if source_path:
			cleanup_file(source_path)


@app.get("/", response_model=dict)
async def root():
	"""Root endpoint"""
	return {
		"message": "FaceFusion API",
		"version": "3.3.0",
		"docs": "/docs",
		"health": "/health"
	}


@app.get("/health", response_model=HealthResponse)
async def health_check():
	"""Health check endpoint"""
	try:
		# Get available processors
		from facefusion import choices
		processors_available = choices.processors

		return HealthResponse(
			status="healthy",
			version="3.3.0",
			processors_available=processors_available
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/processors", response_model=List[ProcessorInfo])
async def list_processors():
	"""List available processors and their status"""
	try:
		from facefusion import choices
		processors = []

		for processor_name in choices.processors:
			try:
				# Try to load processor module
				state_manager.set_item('processors', [processor_name])
				modules = get_processors_modules([processor_name])
				available = len(modules) > 0 and all(m.pre_check() for m in modules)
			except Exception:
				available = False

			processors.append(ProcessorInfo(
				name=processor_name,
				available=available
			))

		return processors
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to list processors: {str(e)}")


@app.post("/process/image", response_model=JobStatus, status_code=202)
async def process_image(
	background_tasks: BackgroundTasks,
	target: UploadFile = File(..., description="Target image to process"),
	source: Optional[UploadFile] = File(None, description="Source image (required for face_swapper)"),
	request: ProcessRequest = ProcessRequest()
):
	"""
	Process an image with specified processors

	- **target**: Target image file (required)
	- **source**: Source image file (optional, required for face_swapper)
	- **request**: Processing parameters
	"""
	job_id: Optional[str] = None
	target_path: Optional[str] = None
	source_path: Optional[str] = None
	job_queued = False

	try:
		logger.init(state_manager.get_item('log_level'))

		target_path = save_upload_file(target)
		if not is_image(target_path):
			raise HTTPException(status_code=400, detail="Target file is not a valid image")

		if processors_require_source(request.processors) and source is None:
			raise HTTPException(status_code=400, detail="Source file is required for the selected processors")

		source_paths: List[str] = []
		if source:
			source_path = save_upload_file(source)
			if not is_image(source_path):
				raise HTTPException(status_code=400, detail="Source file is not a valid image")
			source_paths = [source_path]

		output_filename = f"{uuid.uuid4()}{Path(target_path).suffix}"
		output_path = str(OUTPUT_DIR / output_filename)

		step_args: Args = {
			'source_paths': source_paths,
			'target_path': target_path,
			'output_path': output_path,
			'processors': request.processors,
			'execution_providers': request.execution_providers,
			'execution_thread_count': request.execution_thread_count,
			'output_image_scale': request.output_image_scale,
			'face_detector_model': request.face_detector_model,
			'face_detector_score': request.face_detector_score,
		}

		apply_args(step_args, state_manager.set_item)

		if not common_pre_check():
			raise HTTPException(status_code=500, detail="Common pre-check failed")

		if not processors_pre_check():
			raise HTTPException(status_code=500, detail="Processor pre-check failed")

		jobs_path = state_manager.get_item('jobs_path') or '.jobs'
		if not job_manager.init_jobs(jobs_path):
			raise HTTPException(status_code=500, detail="Failed to initialize job system")

		job_id = job_helper.suggest_job_id('api')
		create_job(job_id, "image", target_path, source_path, output_path)

		if not job_manager.create_job(job_id):
			update_job_status(job_id, "failed", error="Failed to create job")
			job_manager.delete_job(job_id)
			raise HTTPException(status_code=500, detail="Failed to create job")

		if not job_manager.add_step(job_id, step_args):
			update_job_status(job_id, "failed", error="Failed to add job step")
			job_manager.delete_job(job_id)
			raise HTTPException(status_code=500, detail="Failed to add job step")

		if not job_manager.submit_job(job_id):
			update_job_status(job_id, "failed", error="Failed to submit job")
			job_manager.delete_job(job_id)
			raise HTTPException(status_code=500, detail="Failed to submit job")

		update_job_status(job_id, "queued")
		background_tasks.add_task(execute_job, job_id, "image", step_args, target_path, source_path)
		job_queued = True
		return JobStatus(job_id=job_id, status="queued")

	except HTTPException as exc:
		if job_id and not job_queued:
			update_job_status(job_id, "failed", error=str(exc.detail))
		raise
	except Exception as exc:
		logger.error(f"API process_image error: {exc}", __name__)
		if job_id:
			update_job_status(job_id, "failed", error=str(exc))
		raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
	finally:
		if not job_queued:
			if target_path:
				cleanup_file(target_path)
			if source_path:
				cleanup_file(source_path)


@app.post("/process/video", response_model=JobStatus, status_code=202)
async def process_video(
	background_tasks: BackgroundTasks,
	target: UploadFile = File(..., description="Target video to process"),
	source: Optional[UploadFile] = File(None, description="Source image (required for face_swapper)"),
	request: ProcessRequest = ProcessRequest()
):
	"""
	Process a video with specified processors

	- **target**: Target video file (required)
	- **source**: Source image file (optional, required for face_swapper)
	- **request**: Processing parameters
	"""
	job_id: Optional[str] = None
	target_path: Optional[str] = None
	source_path: Optional[str] = None
	job_queued = False

	try:
		logger.init(state_manager.get_item('log_level'))

		target_path = save_upload_file(target)
		if not is_video(target_path):
			raise HTTPException(status_code=400, detail="Target file is not a valid video")

		if processors_require_source(request.processors) and source is None:
			raise HTTPException(status_code=400, detail="Source file is required for the selected processors")

		source_paths: List[str] = []
		if source:
			source_path = save_upload_file(source)
			if not is_image(source_path):
				raise HTTPException(status_code=400, detail="Source file is not a valid image")
			source_paths = [source_path]

		output_filename = f"{uuid.uuid4()}.mp4"
		output_path = str(OUTPUT_DIR / output_filename)

		step_args: Args = {
			'source_paths': source_paths,
			'target_path': target_path,
			'output_path': output_path,
			'processors': request.processors,
			'execution_providers': request.execution_providers,
			'execution_thread_count': request.execution_thread_count,
			'output_video_scale': request.output_video_scale,
			'output_video_fps': request.output_video_fps,
			'face_detector_model': request.face_detector_model,
			'face_detector_score': request.face_detector_score,
		}

		apply_args(step_args, state_manager.set_item)

		if not common_pre_check():
			raise HTTPException(status_code=500, detail="Common pre-check failed")

		if not processors_pre_check():
			raise HTTPException(status_code=500, detail="Processor pre-check failed")

		jobs_path = state_manager.get_item('jobs_path') or '.jobs'
		if not job_manager.init_jobs(jobs_path):
			raise HTTPException(status_code=500, detail="Failed to initialize job system")

		job_id = job_helper.suggest_job_id('api')
		create_job(job_id, "video", target_path, source_path, output_path)

		if not job_manager.create_job(job_id):
			update_job_status(job_id, "failed", error="Failed to create job")
			job_manager.delete_job(job_id)
			raise HTTPException(status_code=500, detail="Failed to create job")

		if not job_manager.add_step(job_id, step_args):
			update_job_status(job_id, "failed", error="Failed to add job step")
			job_manager.delete_job(job_id)
			raise HTTPException(status_code=500, detail="Failed to add job step")

		if not job_manager.submit_job(job_id):
			update_job_status(job_id, "failed", error="Failed to submit job")
			job_manager.delete_job(job_id)
			raise HTTPException(status_code=500, detail="Failed to submit job")

		update_job_status(job_id, "queued")
		background_tasks.add_task(execute_job, job_id, "video", step_args, target_path, source_path)
		job_queued = True
		return JobStatus(job_id=job_id, status="queued")

	except HTTPException as exc:
		if job_id and not job_queued:
			update_job_status(job_id, "failed", error=str(exc.detail))
		raise
	except Exception as exc:
		logger.error(f"API process_video error: {exc}", __name__)
		if job_id:
			update_job_status(job_id, "failed", error=str(exc))
		raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
	finally:
		if not job_queued:
			if target_path:
				cleanup_file(target_path)
			if source_path:
				cleanup_file(source_path)


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
	job = get_job(job_id)
	if not job:
		raise HTTPException(status_code=404, detail="Job not found")
	return map_job_status(job)


@app.get("/jobs", response_model=List[JobStatus])
async def get_jobs(limit: int = Query(50, ge=1, le=200, description="Maximum number of jobs to return")):
	return [map_job_status(job) for job in list_jobs(limit)]


@app.get("/download/{filename}")
async def download_output(
	filename: str,
	background_tasks: BackgroundTasks,
	cleanup: bool = Query(True, description="Auto-delete file after download")
):
	"""
	Download processed output file

	- **filename**: Output filename to download
	- **cleanup**: Whether to delete file after download (default: true)
	"""
	file_path = OUTPUT_DIR / filename

	if not file_path.exists():
		raise HTTPException(status_code=404, detail="Output file not found")

	# Schedule cleanup if requested
	if cleanup:
		background_tasks.add_task(cleanup_file, str(file_path))

	return FileResponse(
		path=str(file_path),
		filename=filename,
		media_type="application/octet-stream"
	)


@app.delete("/output/{filename}")
async def delete_output(filename: str):
	"""Delete an output file"""
	file_path = OUTPUT_DIR / filename

	if not file_path.exists():
		raise HTTPException(status_code=404, detail="Output file not found")

	try:
		os.remove(file_path)
		return {"status": "deleted", "filename": filename}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


def launch_api(host: str = "0.0.0.0", port: int = 8000):
	"""Launch the FastAPI server"""
	import uvicorn
	print(f"[FACEFUSION.API] Starting FastAPI server on {host}:{port}")
	print(f"[FACEFUSION.API] API docs available at http://{host}:{port}/docs")
	uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
	launch_api()
