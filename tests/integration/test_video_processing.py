"""
Integration tests for video processing workflow
Tests face swap on video files
"""

from pathlib import Path

import pytest
import requests

from conftest import download_output, poll_job_status


class TestVideoProcessing:
	"""Test suite for video processing endpoints"""

	def test_video_face_swap_workflow(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_video_path: Path,
		cleanup_outputs: list,
		performance_tracker
	):
		"""
		Complete video face swap workflow:
		1. Upload source image and target video
		2. Submit processing job
		3. Poll until completion (with longer timeout)
		4. Download and verify output
		"""
		print("\n" + "="*60)
		print("FACE SWAP VIDEO PROCESSING TEST")
		print("="*60)

		# Step 1: Submit video processing job
		print("\n[1/4] Submitting video face swap job...")
		performance_tracker.start("video_total_workflow")
		performance_tracker.start("video_submission")

		with open(source_image_path, 'rb') as source_file, \
		     open(target_video_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.mp4', target_file, 'video/mp4')
			}

			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]',
				'execution_thread_count': '2',
				'face_detector_model': 'yoloface_8n',
				'face_detector_score': '0.5',
				'output_video_scale': '100',
				'output_video_fps': 'null'  # Use source FPS
			}

			response = api_client.post(
				f"{api_base_url}/process/video",
				files=files,
				data=data,
				timeout=60
			)

		submission_time = performance_tracker.end("video_submission")

		assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
		job_response = response.json()

		assert "job_id" in job_response
		job_id = job_response["job_id"]
		print(f"  ✓ Job submitted: {job_id}")
		print(f"  ⏱ Submission time: {submission_time:.3f}s")

		# Step 2: Poll for completion (videos take longer)
		print(f"\n[2/4] Polling job status (timeout: 120s for video)...")
		performance_tracker.start("video_processing")

		try:
			# Longer timeout for video processing
			final_status = poll_job_status(
				api_client,
				api_base_url,
				job_id,
				timeout=120,
				poll_interval=3
			)
		except TimeoutError as e:
			pytest.fail(f"Video processing timeout: {e}")

		processing_time = performance_tracker.end("video_processing")

		assert final_status["status"] == "completed", \
			f"Job failed: {final_status.get('error', 'Unknown error')}"
		assert "output_path" in final_status

		print(f"  ✓ Video processing completed")
		print(f"  ⏱ Processing time: {processing_time:.2f}s")
		print(f"  📁 Output path: {final_status['output_path']}")

		# Step 3: Download output video
		print(f"\n[3/4] Downloading output video...")
		performance_tracker.start("video_download")

		output_filename = Path(final_status["output_path"]).name
		local_output = Path("/tmp") / f"facefusion_test_video_{output_filename}"
		cleanup_outputs.append(str(local_output))

		downloaded_path = download_output(
			api_client,
			api_base_url,
			final_status["output_path"],
			local_output
		)

		download_time = performance_tracker.end("video_download")

		print(f"  ✓ Downloaded to: {downloaded_path}")
		print(f"  ⏱ Download time: {download_time:.3f}s")
		print(f"  📊 File size: {downloaded_path.stat().st_size / (1024*1024):.2f} MB")

		# Step 4: Verify output
		print(f"\n[4/4] Verifying output video...")
		assert downloaded_path.exists()
		assert downloaded_path.stat().st_size > 1024, "Video file too small"

		print(f"  ✓ Output video file is valid")

		# Performance summary
		total_time = performance_tracker.end("video_total_workflow")
		print(f"\n" + "="*60)
		print("VIDEO PROCESSING PERFORMANCE SUMMARY")
		print("="*60)
		print(f"  Job submission:  {submission_time:.3f}s")
		print(f"  Video processing: {processing_time:.2f}s")
		print(f"  File download:   {download_time:.3f}s")
		print(f"  Total workflow:  {total_time:.2f}s")
		print("="*60)

	def test_video_processing_without_source(
		self,
		api_client: requests.Session,
		api_base_url: str,
		target_video_path: Path
	):
		"""Test that video face_swapper requires source image"""
		print("\n[TEST] Video processing without source image (should fail)...")

		with open(target_video_path, 'rb') as target_file:
			files = {
				'target': ('target.mp4', target_file, 'video/mp4')
			}

			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]'
			}

			response = api_client.post(
				f"{api_base_url}/process/video",
				files=files,
				data=data,
				timeout=30
			)

		assert response.status_code == 400
		error = response.json()
		assert "source" in error["detail"].lower()

		print(f"  ✓ Correctly rejected: {error['detail']}")

	def test_video_processing_with_custom_fps(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_video_path: Path,
		cleanup_outputs: list
	):
		"""Test video processing with custom FPS"""
		print("\n[TEST] Video processing with custom FPS (30)...")

		with open(source_image_path, 'rb') as source_file, \
		     open(target_video_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.mp4', target_file, 'video/mp4')
			}

			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]',
				'output_video_fps': '30',  # Force 30 FPS
				'output_video_scale': '50'  # Reduce resolution for faster test
			}

			response = api_client.post(
				f"{api_base_url}/process/video",
				files=files,
				data=data,
				timeout=60
			)

		assert response.status_code == 202
		job_id = response.json()["job_id"]
		print(f"  ✓ Job submitted with custom FPS: {job_id}")

		# Poll with extended timeout for video
		final_status = poll_job_status(
			api_client,
			api_base_url,
			job_id,
			timeout=120
		)

		assert final_status["status"] == "completed"
		print(f"  ✓ Video processed with custom FPS successfully")

		# Download to verify
		output_filename = Path(final_status["output_path"]).name
		local_output = Path("/tmp") / f"facefusion_test_fps_{output_filename}"
		cleanup_outputs.append(str(local_output))

		download_output(
			api_client,
			api_base_url,
			final_status["output_path"],
			local_output
		)

		assert local_output.exists()
		print(f"  ✓ Output verified (30 FPS, 50% scale)")
