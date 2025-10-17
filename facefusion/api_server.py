"""
FastAPI REST API server for FaceFusion
Provides OpenAPI-compliant endpoints for external service integration
"""

import os
import uuid
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from facefusion import state_manager, logger, wording
from facefusion.args import apply_args
from facefusion.core import common_pre_check, processors_pre_check, process_step
from facefusion.filesystem import is_image, is_video
from facefusion.jobs import job_helper, job_manager, job_runner
from facefusion.processors.core import get_processors_modules
from facefusion.types import Args


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

# Upload directory
UPLOAD_DIR = Path(".api_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path(".api_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


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


@app.post("/process/image", response_model=JobStatus)
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
	job_id = None
	target_path = None
	source_path = None

	try:
		# Initialize state
		logger.init(state_manager.get_item('log_level'))

		# Save uploaded files
		target_path = save_upload_file(target)
		if not is_image(target_path):
			cleanup_file(target_path)
			raise HTTPException(status_code=400, detail="Target file is not a valid image")

		source_paths = []
		if source:
			source_path = save_upload_file(source)
			if not is_image(source_path):
				cleanup_file(target_path)
				cleanup_file(source_path)
				raise HTTPException(status_code=400, detail="Source file is not a valid image")
			source_paths = [source_path]

		# Generate output path
		output_filename = f"{uuid.uuid4()}{Path(target_path).suffix}"
		output_path = str(OUTPUT_DIR / output_filename)

		# Prepare job arguments
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

		# Apply args to state manager
		apply_args(step_args, state_manager.set_item)

		# Pre-checks
		if not common_pre_check():
			raise HTTPException(status_code=500, detail="Common pre-check failed")

		if not processors_pre_check():
			raise HTTPException(status_code=500, detail="Processor pre-check failed")

		# Initialize job system
		if not job_manager.init_jobs(state_manager.get_item('jobs_path')):
			raise HTTPException(status_code=500, detail="Failed to initialize job system")

		# Create and run job
		job_id = job_helper.suggest_job_id('api')

		if not job_manager.create_job(job_id):
			raise HTTPException(status_code=500, detail="Failed to create job")

		if not job_manager.add_step(job_id, step_args):
			raise HTTPException(status_code=500, detail="Failed to add job step")

		if not job_manager.submit_job(job_id):
			raise HTTPException(status_code=500, detail="Failed to submit job")

		# Run job
		success = job_runner.run_job(job_id, process_step)

		# Schedule cleanup
		background_tasks.add_task(cleanup_file, target_path)
		if source_path:
			background_tasks.add_task(cleanup_file, source_path)

		if success:
			return JobStatus(
				job_id=job_id,
				status="completed",
				output_path=output_path
			)
		else:
			return JobStatus(
				job_id=job_id,
				status="failed",
				error="Job processing failed"
			)

	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"API process_image error: {str(e)}", __name__)
		# Cleanup on error
		if target_path:
			cleanup_file(target_path)
		if source_path:
			cleanup_file(source_path)
		raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/process/video", response_model=JobStatus)
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
	job_id = None
	target_path = None
	source_path = None

	try:
		# Initialize state
		logger.init(state_manager.get_item('log_level'))

		# Save uploaded files
		target_path = save_upload_file(target)
		if not is_video(target_path):
			cleanup_file(target_path)
			raise HTTPException(status_code=400, detail="Target file is not a valid video")

		source_paths = []
		if source:
			source_path = save_upload_file(source)
			if not is_image(source_path):
				cleanup_file(target_path)
				cleanup_file(source_path)
				raise HTTPException(status_code=400, detail="Source file is not a valid image")
			source_paths = [source_path]

		# Generate output path
		output_filename = f"{uuid.uuid4()}.mp4"
		output_path = str(OUTPUT_DIR / output_filename)

		# Prepare job arguments
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

		# Apply args to state manager
		apply_args(step_args, state_manager.set_item)

		# Pre-checks
		if not common_pre_check():
			raise HTTPException(status_code=500, detail="Common pre-check failed")

		if not processors_pre_check():
			raise HTTPException(status_code=500, detail="Processor pre-check failed")

		# Initialize job system
		if not job_manager.init_jobs(state_manager.get_item('jobs_path')):
			raise HTTPException(status_code=500, detail="Failed to initialize job system")

		# Create and run job
		job_id = job_helper.suggest_job_id('api')

		if not job_manager.create_job(job_id):
			raise HTTPException(status_code=500, detail="Failed to create job")

		if not job_manager.add_step(job_id, step_args):
			raise HTTPException(status_code=500, detail="Failed to add job step")

		if not job_manager.submit_job(job_id):
			raise HTTPException(status_code=500, detail="Failed to submit job")

		# Run job
		success = job_runner.run_job(job_id, process_step)

		# Schedule cleanup
		background_tasks.add_task(cleanup_file, target_path)
		if source_path:
			background_tasks.add_task(cleanup_file, source_path)

		if success:
			return JobStatus(
				job_id=job_id,
				status="completed",
				output_path=output_path
			)
		else:
			return JobStatus(
				job_id=job_id,
				status="failed",
				error="Job processing failed"
			)

	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"API process_video error: {str(e)}", __name__)
		# Cleanup on error
		if target_path:
			cleanup_file(target_path)
		if source_path:
			cleanup_file(source_path)
		raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


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
