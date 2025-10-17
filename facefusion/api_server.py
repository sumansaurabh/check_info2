"""
FastAPI REST API server for FaceFusion
Provides OpenAPI-compliant endpoints for external service integration.

The implementation favours lightweight background processing so the API
remains responsive even when running in constrained environments.
"""

import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from PIL import Image, UnidentifiedImageError

from facefusion.env_helper import load_env

load_env()

from facefusion.api_job_store import (
	create_job,
	get_job,
	init_db,
	list_jobs,
	update_job_status
)
from facefusion.filesystem import get_file_name, resolve_file_paths  # noqa: E402
from facefusion.core import process_image as core_process_image, process_video as core_process_video
from facefusion.args import apply_args
from facefusion import logger, state_manager
from facefusion.execution import get_available_execution_providers
from facefusion.program import create_program

init_db()


# Pydantic models for request/response
class ProcessRequest(BaseModel):
	"""Request model for processing operations"""
	processors: List[str] = Field(default_factory=lambda: ["face_swapper"], description="List of processors to apply")
	execution_providers: List[str] = Field(default_factory=lambda: ["cpu"], description="Execution providers (cpu, cuda, etc.)")
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

API_OUTPUT_IMAGE_QUALITY = max(0, min(int(os.getenv("API_OUTPUT_IMAGE_QUALITY", "95")), 100))


def _initialize_state_defaults() -> None:
	try:
		program = create_program()
		default_args = vars(program.parse_args(['run']))
		apply_args(default_args, state_manager.init_item)
	except Exception as exc:
		logger.error(f"[FACEFUSION.API] Failed to initialize default state: {exc}", __name__)
	log_level = state_manager.get_item('log_level') or 'info'
	try:
		logger.init(log_level)
	except Exception:
		logger.error("[FACEFUSION.API] Logger initialization failed; continuing with defaults", __name__)
	state_manager.set_item('command', 'api')
	state_manager.set_item('source_paths', [])
	state_manager.set_item('target_path', None)
	state_manager.set_item('output_path', None)
	state_manager.set_item('output_image_quality', API_OUTPUT_IMAGE_QUALITY)
	if not state_manager.get_item('execution_providers'):
		state_manager.set_item('execution_providers', ['cpu'])
	if not state_manager.get_item('execution_thread_count'):
		state_manager.set_item('execution_thread_count', 1)


_initialize_state_defaults()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _parse_json_like(value: Any) -> Any:
	"""Parse a value that may be JSON-encoded inside a string."""
	if value is None:
		return None
	if isinstance(value, (list, dict, int, float, bool)):
		return value
	if isinstance(value, str):
		stripped = value.strip()
		if stripped == "":
			return None
		if stripped.lower() in {"null", "none"}:
			return None
		try:
			return json.loads(stripped)
		except json.JSONDecodeError:
			return value
	return value


def _ensure_list(value: Any, default: List[str]) -> List[str]:
	parsed = _parse_json_like(value)
	if parsed is None:
		return list(default)
	if isinstance(parsed, list):
		return [str(item) for item in parsed if str(item).strip()]
	return [str(parsed)]


def _ensure_int(value: Any, default: int, minimum: int, maximum: int) -> int:
	parsed = _parse_json_like(value)
	if isinstance(parsed, (int, float)):
		number = int(parsed)
	elif isinstance(parsed, str):
		try:
			number = int(float(parsed))
		except ValueError:
			return default
	else:
		return default
	return max(minimum, min(maximum, number))


def _ensure_float(value: Any, default: float, minimum: float, maximum: float) -> float:
	parsed = _parse_json_like(value)
	if isinstance(parsed, (int, float)):
		number = float(parsed)
	elif isinstance(parsed, str):
		try:
			number = float(parsed)
		except ValueError:
			return default
	else:
		return default
	return max(minimum, min(maximum, number))


def _build_process_request(data: dict[str, Any]) -> ProcessRequest:
	return ProcessRequest.model_validate(data)


def _sanitize_processors(processors: List[str]) -> List[str]:
	sanitized = [str(processor).strip() for processor in processors if str(processor).strip()]
	if not sanitized:
		logger.warn("[FACEFUSION.API] No valid processors requested; defaulting to face_swapper", __name__)
		return ["face_swapper"]
	return sanitized


def _select_execution_providers(requested: List[str]) -> List[str]:
	available = get_available_execution_providers() or ['cpu']
	requested_normalized = []

	for provider in requested:
		name = str(provider).strip().lower()
		if name:
			requested_normalized.append(name)

	selected: List[str] = []

	for provider in requested_normalized:
		if provider in available and provider not in selected:
			selected.append(provider)

	if not selected:
		if requested_normalized:
			logger.warn(
				f"[FACEFUSION.API] Requested execution providers {requested_normalized} are not available; "
				f"falling back to CPU",
				__name__
			)
		selected = ['cpu'] if 'cpu' in available else [available[0]]

	if 'cpu' not in selected and 'cpu' in available:
		selected.append('cpu')

	return selected


def _percentage_to_scale(value: int) -> float:
	return max(value, 1) / 100.0


def _prepare_image_job_state(step_args: dict) -> dict:
	processors = _sanitize_processors(step_args.get('processors', []))
	execution_providers = _select_execution_providers(step_args.get('execution_providers', []))
	source_paths = [path for path in step_args.get('source_paths', []) if path]
	target_path = step_args.get('target_path')
	output_path = step_args.get('output_path')
	output_image_scale = _percentage_to_scale(step_args.get('output_image_scale', 100))

	state_manager.set_item('command', 'api')
	state_manager.set_item('processors', processors)
	state_manager.set_item('source_paths', source_paths)
	state_manager.set_item('target_path', target_path)
	state_manager.set_item('output_path', output_path)
	state_manager.set_item('execution_providers', execution_providers)
	state_manager.set_item('execution_thread_count', step_args.get('execution_thread_count', 1))
	state_manager.set_item('output_image_scale', output_image_scale)
	state_manager.set_item('face_detector_model', step_args.get('face_detector_model'))
	state_manager.set_item('face_detector_score', step_args.get('face_detector_score'))
	state_manager.set_item('face_swapper_model', step_args.get('face_swapper_model'))
	state_manager.set_item('face_enhancer_model', step_args.get('face_enhancer_model'))
	state_manager.set_item('face_enhancer_blend', step_args.get('face_enhancer_blend'))

	return {
		'processors': processors,
		'execution_providers': execution_providers,
		'source_paths': source_paths,
		'target_path': target_path,
		'output_path': output_path,
		'output_image_scale': output_image_scale
	}


def _prepare_video_job_state(step_args: dict) -> dict:
	processors = _sanitize_processors(step_args.get('processors', []))
	execution_providers = _select_execution_providers(step_args.get('execution_providers', []))
	source_paths = [path for path in step_args.get('source_paths', []) if path]
	target_path = step_args.get('target_path')
	output_path = step_args.get('output_path')
	output_video_scale = _percentage_to_scale(step_args.get('output_video_scale', 100))

	state_manager.set_item('command', 'api')
	state_manager.set_item('processors', processors)
	state_manager.set_item('source_paths', source_paths)
	state_manager.set_item('target_path', target_path)
	state_manager.set_item('output_path', output_path)
	state_manager.set_item('execution_providers', execution_providers)
	state_manager.set_item('execution_thread_count', step_args.get('execution_thread_count', 1))
	state_manager.set_item('output_video_scale', output_video_scale)
	state_manager.set_item('face_detector_model', step_args.get('face_detector_model'))
	state_manager.set_item('face_detector_score', step_args.get('face_detector_score'))

	output_video_fps = step_args.get('output_video_fps')
	if output_video_fps is not None:
		state_manager.set_item('output_video_fps', float(output_video_fps))

	return {
		'processors': processors,
		'execution_providers': execution_providers,
		'source_paths': source_paths,
		'target_path': target_path,
		'output_path': output_path,
		'output_video_scale': output_video_scale,
		'output_video_fps': output_video_fps
	}


def save_upload_file(upload_file: UploadFile) -> str:
	"""Save uploaded file and return path"""
	file_ext = Path(upload_file.filename or "").suffix or ""
	file_id = uuid.uuid4().hex
	file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

	with open(file_path, "wb") as f:
		f.write(upload_file.file.read())

	return str(file_path)


def cleanup_file(file_path: Optional[str]) -> None:
	"""Clean up temporary file"""
	if not file_path:
		return
	try:
		if os.path.exists(file_path):
			os.remove(file_path)
	except Exception:
		# Silently ignore cleanup errors to keep background tasks resilient
		pass


def processors_require_source(processors: List[str]) -> bool:
	required = {"face_swapper", "deep_swapper"}
	return any(processor in required for processor in processors)


def map_job_status(job: dict) -> JobStatus:
	return JobStatus(
		job_id=job.get("job_id"),
		status=job.get("status"),
		output_path=job.get("output_path"),
		error=job.get("error")
	)


def _generate_job_id(prefix: str = "api") -> str:
	return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _validate_image_file(file_path: str) -> None:
	try:
		with Image.open(file_path) as img:
			img.verify()
	except UnidentifiedImageError:
		raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")
	except Exception as exc:
		raise HTTPException(status_code=400, detail=f"Failed to read image: {exc}") from exc





def _execute_image_job(job_id: str, step_args: dict) -> None:
	prepared: dict[str, Any] = {}
	try:
		prepared = _prepare_image_job_state(step_args)
		update_job_status(job_id, "running")
		processing_args = {
			'source_paths': prepared.get('source_paths', []),
			'target_path': prepared.get('target_path'),
			'output_path': prepared.get('output_path'),
			'processors': prepared.get('processors', []),
			'execution_providers': prepared.get('execution_providers', []),
			'execution_thread_count': int(step_args.get('execution_thread_count', 1)),
			'output_image_scale': prepared.get('output_image_scale', 1.0),
			'face_detector_model': step_args.get('face_detector_model'),
			'face_detector_score': float(step_args.get('face_detector_score', 0.5)),
			'face_swapper_model': step_args.get('face_swapper_model'),
			'face_enhancer_model': step_args.get('face_enhancer_model'),
			'face_enhancer_blend': int(step_args.get('face_enhancer_blend', 0))
		}

		result = core_process_image(**processing_args)
		if result != 0:
			raise RuntimeError(f"FaceFusion core returned error code {result}")

		output_path = processing_args.get('output_path')
		if not output_path or not os.path.exists(output_path):
			raise FileNotFoundError("Output file was not created")
		if os.path.getsize(output_path) == 0:
			raise RuntimeError("Output file is empty")

		update_job_status(job_id, "completed", output_path=output_path)
	except Exception as exc:
		update_job_status(job_id, "failed", error=str(exc))
	finally:
		cleanup_file(prepared.get('target_path') or step_args.get('target_path'))
		for source_path in prepared.get('source_paths', step_args.get('source_paths', [])):
			cleanup_file(source_path)


def _execute_video_job(job_id: str, step_args: dict) -> None:
	prepared: dict[str, Any] = {}
	try:
		prepared = _prepare_video_job_state(step_args)
		update_job_status(job_id, "running")
		result = core_process_video(time.time())
		if result != 0:
			raise RuntimeError(f"FaceFusion core returned error code {result}")

		output_path = state_manager.get_item('output_path') or prepared.get('output_path')
		if not output_path or not os.path.exists(output_path):
			raise FileNotFoundError("Output file was not created")
		if os.path.getsize(output_path) == 0:
			raise RuntimeError("Output file is empty")

		update_job_status(job_id, "completed", output_path=output_path)
	except Exception as exc:
		update_job_status(job_id, "failed", error=str(exc))
	finally:
		cleanup_file(prepared.get('target_path') or state_manager.get_item('target_path'))
		source_paths = prepared.get('source_paths') or state_manager.get_item('source_paths') or []
		for source_path in source_paths:
			cleanup_file(source_path)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

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
	processors_available = [get_file_name(file_path) for file_path in resolve_file_paths('facefusion/processors/modules')]
	return HealthResponse(
		status="healthy",
		version="3.3.0",
		processors_available=processors_available
	)


@app.get("/processors", response_model=List[ProcessorInfo])
async def list_processors():
	"""List available processors and their status"""
	processors = []
	for processor_name in [get_file_name(file_path) for file_path in resolve_file_paths('facefusion/processors/modules')]:
		if processor_name:
			processors.append(ProcessorInfo(name=processor_name, available=True))
	return processors


@app.post("/process/image", response_model=JobStatus, status_code=202)
async def process_image(
	background_tasks: BackgroundTasks,
	target: UploadFile = File(..., description="Target image to process"),
	source: Optional[UploadFile] = File(None, description="Source image (required for face_swapper)"),
	processors: Optional[str] = Form(None),
	execution_providers: Optional[str] = Form(None),
	execution_thread_count: Optional[str] = Form(None),
	output_image_scale: Optional[str] = Form(None),
	face_detector_model: Optional[str] = Form(None),
	face_detector_score: Optional[str] = Form(None),
	face_swapper_model: Optional[str] = Form(None),
	face_enhancer_model: Optional[str] = Form(None),
	face_enhancer_blend: Optional[str] = Form(None)
):
	"""
	Process an image with specified processors

	- **target**: Target image file (required)
	- **source**: Source image file (optional, required for face_swapper)
	- **processors**: JSON string/list of processors
	"""
	job_id: Optional[str] = None
	target_path: Optional[str] = None
	source_path: Optional[str] = None
	job_queued = False

	try:
		target_path = save_upload_file(target)
		_validate_image_file(target_path)

		request_data = {
			'processors': _ensure_list(processors, ["face_swapper"]),
			'execution_providers': _ensure_list(execution_providers, ["cpu"]),
			'execution_thread_count': _ensure_int(execution_thread_count, 1, 1, 32),
			'output_image_scale': _ensure_int(output_image_scale, 100, 10, 400),
			'face_detector_model': face_detector_model or "yoloface_8n",
			'face_detector_score': _ensure_float(face_detector_score, 0.5, 0.0, 1.0),
			'face_swapper_model': face_swapper_model or 'inswapper_128',
			'face_enhancer_model': face_enhancer_model or 'gfpgan_1.4',
			'face_enhancer_blend': _ensure_int(face_enhancer_blend, 80, 0, 100)
		}
		try:
			request = _build_process_request(request_data)
		except ValidationError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc

		if processors_require_source(request.processors) and source is None:
			raise HTTPException(status_code=400, detail="Source file is required for the selected processors")

		if source:
			source_path = save_upload_file(source)
			_validate_image_file(source_path)

		output_filename = f"{uuid.uuid4().hex}.jpg"
		output_path = str(OUTPUT_DIR / output_filename)

		job_id = _generate_job_id("image")
		create_job(job_id, "image", target_path, source_path, output_path)
		update_job_status(job_id, "queued")

		step_args = request_data.copy()
		step_args['source_paths'] = [source_path] if source_path else []
		step_args['target_path'] = target_path
		step_args['output_path'] = output_path

		background_tasks.add_task(
			_execute_image_job,
			job_id,
			step_args
		)
		job_queued = True
		return JobStatus(job_id=job_id, status="queued")

	except HTTPException:
		raise
	except Exception as exc:
		if job_id:
			update_job_status(job_id, "failed", error=str(exc))
		raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc
	finally:
		if not job_queued:
			cleanup_file(target_path)
			cleanup_file(source_path)


@app.post("/process/video", response_model=JobStatus, status_code=202)
async def process_video(
	background_tasks: BackgroundTasks,
	target: UploadFile = File(..., description="Target video to process"),
	source: Optional[UploadFile] = File(None, description="Source image (required for face_swapper)"),
	processors: Optional[str] = Form(None),
	execution_providers: Optional[str] = Form(None),
	execution_thread_count: Optional[str] = Form(None),
	output_video_scale: Optional[str] = Form(None),
	output_video_fps: Optional[str] = Form(None),
	face_detector_model: Optional[str] = Form(None),
	face_detector_score: Optional[str] = Form(None)
):
	"""
	Process a video with specified processors.
	The current implementation performs placeholder processing (file copy).
	"""
	job_id: Optional[str] = None
	target_path: Optional[str] = None
	source_path: Optional[str] = None
	job_queued = False

	try:
		target_path = save_upload_file(target)

		request_data = {
			'processors': _ensure_list(processors, ["face_swapper"]),
			'execution_providers': _ensure_list(execution_providers, ["cpu"]),
			'execution_thread_count': _ensure_int(execution_thread_count, 1, 1, 32),
			'output_video_scale': _ensure_int(output_video_scale, 100, 10, 400),
			'output_video_fps': _parse_json_like(output_video_fps),
			'face_detector_model': face_detector_model or "yoloface_8n",
			'face_detector_score': _ensure_float(face_detector_score, 0.5, 0.0, 1.0)
		}
		try:
			request = _build_process_request(request_data)
		except ValidationError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc

		if processors_require_source(request.processors) and source is None:
			raise HTTPException(status_code=400, detail="Source file is required for the selected processors")

		if source:
			source_path = save_upload_file(source)
			_validate_image_file(source_path)

		output_filename = f"{uuid.uuid4().hex}.mp4"
		output_path = str(OUTPUT_DIR / output_filename)

		job_id = _generate_job_id("video")
		create_job(job_id, "video", target_path, source_path, output_path)
		update_job_status(job_id, "queued")

		step_args = request_data.copy()
		step_args['source_paths'] = [source_path] if source_path else []
		step_args['target_path'] = target_path
		step_args['output_path'] = output_path

		background_tasks.add_task(
			_execute_video_job,
			job_id,
			step_args
		)
		job_queued = True
		return JobStatus(job_id=job_id, status="queued")

	except HTTPException:
		raise
	except Exception as exc:
		if job_id:
			update_job_status(job_id, "failed", error=str(exc))
		raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc
	finally:
		if not job_queued:
			cleanup_file(target_path)
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
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}") from exc


def launch_api(host: str = "0.0.0.0", port: int = 8000):
	"""Launch the FastAPI server"""
	import uvicorn
	print(f"[FACEFUSION.API] Starting FastAPI server on {host}:{port}")
	print(f"[FACEFUSION.API] API docs available at http://{host}:{port}/docs")
	uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
	launch_api()
