"""
Integration tests for image processing workflow
Tests complete face swap pipeline: upload -> process -> poll -> download
"""

from pathlib import Path

import pytest
import requests

from conftest import download_output, poll_job_status, verify_image_output


class TestImageProcessing:
	"""Test suite for image processing endpoints and workflows"""

	def test_image_face_swap_complete_workflow(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_image_path: Path,
		cleanup_outputs: list,
		performance_tracker
	):
		"""
		Complete face swap workflow test:
		1. Upload source and target images
		2. Submit processing job
		3. Poll until completion
		4. Download and verify output
		"""
		print("\n" + "="*60)
		print("FACE SWAP IMAGE PROCESSING TEST")
		print("="*60)

		# Step 1: Submit processing job
		print("\n[1/4] Submitting face swap job...")
		performance_tracker.start("total_workflow")
		performance_tracker.start("job_submission")

		with open(source_image_path, 'rb') as source_file, \
		     open(target_image_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			# Use inswapper_128 for fastest test performance
			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]',
				'execution_thread_count': '1',
				'face_detector_model': 'yoloface_8n',
				'face_detector_score': '0.5',
				'output_image_scale': '100'
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				data=data,
				timeout=30
			)

		submission_time = performance_tracker.end("job_submission")

		# Verify job was accepted
		assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
		job_response = response.json()

		assert "job_id" in job_response
		assert "status" in job_response
		assert job_response["status"] == "queued"

		job_id = job_response["job_id"]
		print(f"  ✓ Job submitted: {job_id}")
		print(f"  ⏱ Submission time: {submission_time:.3f}s")

		# Step 2: Poll for completion
		print(f"\n[2/4] Polling job status (timeout: 60s)...")
		performance_tracker.start("job_processing")

		try:
			final_status = poll_job_status(api_client, api_base_url, job_id, timeout=60)
		except TimeoutError as e:
			pytest.fail(f"Job processing timeout: {e}")

		processing_time = performance_tracker.end("job_processing")

		# Verify completion
		assert final_status["status"] == "completed", \
			f"Job failed: {final_status.get('error', 'Unknown error')}"
		assert "output_path" in final_status
		assert final_status["output_path"] is not None

		print(f"  ✓ Job completed successfully")
		print(f"  ⏱ Processing time: {processing_time:.2f}s")
		print(f"  📁 Output path: {final_status['output_path']}")

		# Step 3: Download output
		print(f"\n[3/4] Downloading output image...")
		performance_tracker.start("download")

		output_filename = Path(final_status["output_path"]).name
		local_output = Path("/tmp") / f"facefusion_test_{output_filename}"
		cleanup_outputs.append(str(local_output))

		downloaded_path = download_output(
			api_client,
			api_base_url,
			final_status["output_path"],
			local_output,
			cleanup=False  # Don't cleanup yet, we'll do it via API
		)

		download_time = performance_tracker.end("download")

		print(f"  ✓ Downloaded to: {downloaded_path}")
		print(f"  ⏱ Download time: {download_time:.3f}s")
		print(f"  📊 File size: {downloaded_path.stat().st_size / 1024:.1f} KB")

		# Step 4: Verify output
		print(f"\n[4/4] Verifying output image...")
		verify_image_output(downloaded_path, min_size_kb=10)
		print(f"  ✓ Output image is valid")

		# Performance summary
		total_time = performance_tracker.end("total_workflow")
		print(f"\n" + "="*60)
		print("PERFORMANCE SUMMARY")
		print("="*60)
		print(f"  Job submission:  {submission_time:.3f}s")
		print(f"  Job processing:  {processing_time:.2f}s")
		print(f"  File download:   {download_time:.3f}s")
		print(f"  Total workflow:  {total_time:.2f}s")
		print("="*60)

		# Performance assertions
		assert submission_time < 5.0, "Job submission too slow"
		assert processing_time < 60.0, "Processing took too long"
		assert download_time < 10.0, "Download too slow"

	def test_image_processing_without_source(
		self,
		api_client: requests.Session,
		api_base_url: str,
		target_image_path: Path
	):
		"""Test that face_swapper requires source image"""
		print("\n[TEST] Processing without source image (should fail)...")

		with open(target_image_path, 'rb') as target_file:
			files = {
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]'
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				data=data,
				timeout=30
			)

		# Should return 400 Bad Request
		assert response.status_code == 400
		error = response.json()
		assert "detail" in error
		assert "source" in error["detail"].lower()

		print(f"  ✓ Correctly rejected: {error['detail']}")

	def test_image_processing_invalid_target(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		tmp_path: Path
	):
		"""Test processing with invalid target file"""
		print("\n[TEST] Processing with invalid target file...")

		# Create invalid "image" file
		invalid_file = tmp_path / "invalid.jpg"
		invalid_file.write_text("This is not an image")

		with open(source_image_path, 'rb') as source_file, \
		     open(invalid_file, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('invalid.jpg', target_file, 'image/jpeg')
			}

			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]'
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				data=data,
				timeout=30
			)

		# Should return 400 Bad Request
		assert response.status_code == 400
		error = response.json()
		assert "detail" in error

		print(f"  ✓ Correctly rejected invalid file: {error['detail']}")

	def test_image_processing_with_custom_parameters(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_image_path: Path,
		cleanup_outputs: list
	):
		"""Test image processing with custom parameters"""
		print("\n[TEST] Face swap with custom parameters...")

		with open(source_image_path, 'rb') as source_file, \
		     open(target_image_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			# Custom parameters
			data = {
				'processors': '["face_swapper"]',
				'execution_providers': '["cpu"]',
				'execution_thread_count': '2',
				'face_detector_model': 'yoloface_8n',
				'face_detector_score': '0.6',  # Higher threshold
				'output_image_scale': '150'  # 1.5x scale
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				data=data,
				timeout=30
			)

		assert response.status_code == 202
		job_response = response.json()
		job_id = job_response["job_id"]

		print(f"  ✓ Job submitted with custom params: {job_id}")

		# Poll for completion
		final_status = poll_job_status(api_client, api_base_url, job_id, timeout=60)

		assert final_status["status"] == "completed", \
			f"Job failed: {final_status.get('error')}"

		print(f"  ✓ Custom parameters processed successfully")

		# Download and verify output
		output_filename = Path(final_status["output_path"]).name
		local_output = Path("/tmp") / f"facefusion_test_custom_{output_filename}"
		cleanup_outputs.append(str(local_output))

		downloaded_path = download_output(
			api_client,
			api_base_url,
			final_status["output_path"],
			local_output
		)

		verify_image_output(downloaded_path, min_size_kb=10)
		print(f"  ✓ Output verified (scale 150%)")
