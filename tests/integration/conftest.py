"""
Integration Test Configuration and Fixtures
Provides shared fixtures for API testing with localhost server
"""

import os
import time
from pathlib import Path
from typing import Generator, Optional

import pytest
import requests
from PIL import Image


# Test Configuration
API_BASE_URL = os.getenv("FACEFUSION_API_URL", "http://129.146.117.178:8000")
API_TIMEOUT = 10  # seconds for API calls
JOB_POLL_TIMEOUT = 60  # seconds for job completion
JOB_POLL_INTERVAL = 2  # seconds between polls

# Test Fixtures Directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def api_base_url() -> str:
	"""Base URL for the FaceFusion API server"""
	return API_BASE_URL


@pytest.fixture(scope="session")
def api_client(api_base_url: str) -> requests.Session:
	"""
	Configured requests session for API calls
	Includes retries and timeout configuration
	"""
	session = requests.Session()
	session.headers.update({
		"User-Agent": "FaceFusion-Integration-Test/1.0"
	})

	# Verify API is reachable
	max_retries = 5
	retry_delay = 2

	for attempt in range(max_retries):
		try:
			response = session.get(f"{api_base_url}/health", timeout=API_TIMEOUT)
			if response.status_code == 200:
				print(f"\n✓ API server is healthy at {api_base_url}")
				break
		except requests.exceptions.RequestException as e:
			if attempt < max_retries - 1:
				print(f"\n⚠ API not ready (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
				time.sleep(retry_delay)
			else:
				pytest.fail(f"API server not reachable at {api_base_url}: {e}")

	yield session
	session.close()


@pytest.fixture(scope="session")
def source_image_path() -> Path:
	"""Path to source face image fixture"""
	path = FIXTURES_DIR / "source.jpg"

	if not path.exists():
		# Create placeholder image with instructions
		_create_placeholder_image(path, "SOURCE FACE", (512, 512))
		pytest.skip(f"Please add source face image to: {path}")

	return path


@pytest.fixture(scope="session")
def target_image_path() -> Path:
	"""Path to target image fixture"""
	path = FIXTURES_DIR / "target.jpg"

	if not path.exists():
		# Create placeholder image with instructions
		_create_placeholder_image(path, "TARGET IMAGE", (512, 512))
		pytest.skip(f"Please add target image to: {path}")

	return path


@pytest.fixture(scope="session")
def target_video_path() -> Path:
	"""Path to target video fixture"""
	path = FIXTURES_DIR / "target.mp4"

	if not path.exists():
		pytest.skip(f"Please add target video to: {path}")

	return path


@pytest.fixture
def cleanup_outputs() -> Generator[list, None, None]:
	"""
	Track downloaded output files for cleanup after tests
	Usage: cleanup_outputs.append(file_path)
	"""
	output_files = []
	yield output_files

	# Cleanup after test
	for file_path in output_files:
		if Path(file_path).exists():
			Path(file_path).unlink()


def _create_placeholder_image(path: Path, text: str, size: tuple[int, int]) -> None:
	"""Create a placeholder image with text"""
	from PIL import ImageDraw, ImageFont

	img = Image.new('RGB', size, color=(73, 109, 137))
	draw = ImageDraw.Draw(img)

	# Try to use a default font, fallback to basic
	try:
		font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
	except:
		font = ImageFont.load_default()

	# Center text
	bbox = draw.textbbox((0, 0), text, font=font)
	text_width = bbox[2] - bbox[0]
	text_height = bbox[3] - bbox[1]
	position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)

	draw.text(position, text, fill=(255, 255, 255), font=font)
	img.save(path, 'JPEG', quality=95)
	print(f"\n📝 Created placeholder image: {path}")
	print(f"   Please replace with actual test image containing a face")


def poll_job_status(
	api_client: requests.Session,
	api_base_url: str,
	job_id: str,
	timeout: int = JOB_POLL_TIMEOUT,
	poll_interval: int = JOB_POLL_INTERVAL
) -> dict:
	"""
	Poll job status until completion or timeout

	Args:
		api_client: Requests session
		api_base_url: Base API URL
		job_id: Job ID to poll
		timeout: Maximum time to wait in seconds
		poll_interval: Time between polls in seconds

	Returns:
		Final job status dict

	Raises:
		TimeoutError: If job doesn't complete within timeout
		requests.RequestException: If API call fails
	"""
	start_time = time.time()

	while True:
		elapsed = time.time() - start_time

		if elapsed > timeout:
			raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

		response = api_client.get(
			f"{api_base_url}/jobs/{job_id}",
			timeout=API_TIMEOUT
		)
		response.raise_for_status()

		job_status = response.json()
		status = job_status.get("status")

		print(f"  [{elapsed:.1f}s] Job {job_id}: {status}")

		if status in ["completed", "failed"]:
			return job_status

		time.sleep(poll_interval)


def download_output(
	api_client: requests.Session,
	api_base_url: str,
	output_path: str,
	save_to: Path,
	cleanup: bool = False
) -> Path:
	"""
	Download output file from API

	Args:
		api_client: Requests session
		api_base_url: Base API URL
		output_path: Output path from job status
		save_to: Local path to save file
		cleanup: Whether to request server-side cleanup

	Returns:
		Path to downloaded file
	"""
	filename = Path(output_path).name

	response = api_client.get(
		f"{api_base_url}/download/{filename}",
		params={"cleanup": str(cleanup).lower()},
		timeout=30,
		stream=True
	)
	response.raise_for_status()

	save_to.parent.mkdir(parents=True, exist_ok=True)

	with open(save_to, 'wb') as f:
		for chunk in response.iter_content(chunk_size=8192):
			f.write(chunk)

	return save_to


def verify_image_output(image_path: Path, min_size_kb: int = 10) -> bool:
	"""
	Verify output image is valid and reasonable size

	Args:
		image_path: Path to image file
		min_size_kb: Minimum expected file size in KB

	Returns:
		True if valid

	Raises:
		AssertionError: If validation fails
	"""
	assert image_path.exists(), f"Output file not found: {image_path}"

	file_size_kb = image_path.stat().st_size / 1024
	assert file_size_kb >= min_size_kb, f"Output file too small: {file_size_kb:.1f}KB < {min_size_kb}KB"

	# Verify it's a valid image
	try:
		with Image.open(image_path) as img:
			assert img.size[0] > 0 and img.size[1] > 0, "Invalid image dimensions"
			assert img.mode in ['RGB', 'RGBA', 'L'], f"Unexpected image mode: {img.mode}"
	except Exception as e:
		raise AssertionError(f"Invalid image file: {e}")

	return True


@pytest.fixture
def performance_tracker():
	"""Track performance metrics for tests"""
	class PerformanceTracker:
		def __init__(self):
			self.metrics = {}
			self.start_times = {}

		def start(self, name: str):
			"""Start timing an operation"""
			self.start_times[name] = time.time()

		def end(self, name: str) -> float:
			"""End timing and return duration"""
			if name not in self.start_times:
				raise ValueError(f"Timer '{name}' not started")

			duration = time.time() - self.start_times[name]
			self.metrics[name] = duration
			del self.start_times[name]
			return duration

		def get(self, name: str) -> Optional[float]:
			"""Get recorded metric"""
			return self.metrics.get(name)

		def report(self) -> str:
			"""Generate performance report"""
			if not self.metrics:
				return "No metrics recorded"

			lines = ["Performance Metrics:"]
			for name, duration in sorted(self.metrics.items()):
				lines.append(f"  {name}: {duration:.2f}s")
			return "\n".join(lines)

	return PerformanceTracker()
