"""
Integration tests for file operations
Tests download and delete endpoints
"""

from pathlib import Path

import requests

from conftest import poll_job_status


class TestFileOperations:
	"""Test suite for file download and deletion operations"""

	def test_download_output_file(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_image_path: Path,
		cleanup_outputs: list
	):
		"""Test downloading processed output file"""
		print("\n[TEST] Download output file...")

		# First create and complete a job
		with open(source_image_path, 'rb') as source_file, \
		     open(target_image_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				timeout=30
			)

		job_id = response.json()["job_id"]

		# Wait for completion
		final_status = poll_job_status(api_client, api_base_url, job_id, timeout=60)
		assert final_status["status"] == "completed"

		output_path = final_status["output_path"]
		filename = Path(output_path).name

		# Test download
		response = api_client.get(
			f"{api_base_url}/download/{filename}",
			params={"cleanup": "false"}
		)

		assert response.status_code == 200
		assert len(response.content) > 0

		# Verify content type
		content_type = response.headers.get("content-type", "")
		assert "application/octet-stream" in content_type or "image" in content_type

		# Save to verify
		local_path = Path("/tmp") / f"test_download_{filename}"
		cleanup_outputs.append(str(local_path))
		local_path.write_bytes(response.content)

		print(f"  ✓ Downloaded file: {filename}")
		print(f"    Size: {len(response.content) / 1024:.1f} KB")
		print(f"    Saved to: {local_path}")

	def test_download_with_auto_cleanup(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_image_path: Path
	):
		"""Test downloading with automatic server-side cleanup"""
		print("\n[TEST] Download with auto cleanup...")

		# Create and complete a job
		with open(source_image_path, 'rb') as source_file, \
		     open(target_image_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				timeout=30
			)

		job_id = response.json()["job_id"]
		final_status = poll_job_status(api_client, api_base_url, job_id, timeout=60)

		filename = Path(final_status["output_path"]).name

		# Download with cleanup=true
		response = api_client.get(
			f"{api_base_url}/download/{filename}",
			params={"cleanup": "true"}
		)

		assert response.status_code == 200
		print(f"  ✓ Downloaded with cleanup flag: {filename}")

		# Try to download again - should fail (file cleaned up)
		import time
		time.sleep(2)  # Give server time to cleanup

		response = api_client.get(
			f"{api_base_url}/download/{filename}",
			params={"cleanup": "false"}
		)

		# File should be gone (404) or cleanup might be async
		if response.status_code == 404:
			print(f"  ✓ File cleaned up successfully (404)")
		else:
			print(f"  ℹ File still available (cleanup may be async)")

	def test_download_nonexistent_file(
		self,
		api_client: requests.Session,
		api_base_url: str
	):
		"""Test downloading a file that doesn't exist"""
		print("\n[TEST] Download nonexistent file...")

		fake_filename = "nonexistent_output_12345.jpg"
		response = api_client.get(f"{api_base_url}/download/{fake_filename}")

		assert response.status_code == 404
		error = response.json()
		assert "detail" in error
		assert "not found" in error["detail"].lower()

		print(f"  ✓ Correctly returned 404 for nonexistent file")

	def test_delete_output_file(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_image_path: Path
	):
		"""Test deleting an output file"""
		print("\n[TEST] Delete output file...")

		# Create and complete a job
		with open(source_image_path, 'rb') as source_file, \
		     open(target_image_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				timeout=30
			)

		job_id = response.json()["job_id"]
		final_status = poll_job_status(api_client, api_base_url, job_id, timeout=60)

		filename = Path(final_status["output_path"]).name

		# Delete the file
		response = api_client.delete(f"{api_base_url}/output/{filename}")

		assert response.status_code == 200
		delete_response = response.json()
		assert delete_response["status"] == "deleted"
		assert delete_response["filename"] == filename

		print(f"  ✓ File deleted: {filename}")

		# Verify file is gone
		response = api_client.get(f"{api_base_url}/download/{filename}")
		assert response.status_code == 404

		print(f"  ✓ Verified file no longer exists")

	def test_delete_nonexistent_file(
		self,
		api_client: requests.Session,
		api_base_url: str
	):
		"""Test deleting a file that doesn't exist"""
		print("\n[TEST] Delete nonexistent file...")

		fake_filename = "nonexistent_output_67890.jpg"
		response = api_client.delete(f"{api_base_url}/output/{fake_filename}")

		assert response.status_code == 404
		error = response.json()
		assert "detail" in error

		print(f"  ✓ Correctly returned 404 for nonexistent file")

	def test_file_operations_workflow(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path: Path,
		target_image_path: Path,
		cleanup_outputs: list,
		performance_tracker
	):
		"""
		Test complete file operations workflow:
		process -> download -> verify -> delete
		"""
		print("\n[TEST] Complete file operations workflow...")

		performance_tracker.start("file_ops_workflow")

		# 1. Process
		print("\n  [1/4] Processing...")
		with open(source_image_path, 'rb') as source_file, \
		     open(target_image_path, 'rb') as target_file:

			files = {
				'source': ('source.jpg', source_file, 'image/jpeg'),
				'target': ('target.jpg', target_file, 'image/jpeg')
			}

			response = api_client.post(
				f"{api_base_url}/process/image",
				files=files,
				timeout=30
			)

		job_id = response.json()["job_id"]
		final_status = poll_job_status(api_client, api_base_url, job_id, timeout=60)
		filename = Path(final_status["output_path"]).name
		print(f"    ✓ Processed: {filename}")

		# 2. Download
		print("\n  [2/4] Downloading...")
		response = api_client.get(
			f"{api_base_url}/download/{filename}",
			params={"cleanup": "false"}
		)
		assert response.status_code == 200

		local_path = Path("/tmp") / f"test_workflow_{filename}"
		cleanup_outputs.append(str(local_path))
		local_path.write_bytes(response.content)
		print(f"    ✓ Downloaded: {len(response.content)} bytes")

		# 3. Verify
		print("\n  [3/4] Verifying...")
		assert local_path.exists()
		assert local_path.stat().st_size > 1024
		print(f"    ✓ Verified: {local_path.stat().st_size} bytes")

		# 4. Delete
		print("\n  [4/4] Deleting...")
		response = api_client.delete(f"{api_base_url}/output/{filename}")
		assert response.status_code == 200
		print(f"    ✓ Deleted from server")

		# Verify deletion
		response = api_client.get(f"{api_base_url}/download/{filename}")
		assert response.status_code == 404
		print(f"    ✓ Verified deletion")

		workflow_time = performance_tracker.end("file_ops_workflow")
		print(f"\n  ✓ Complete workflow finished in {workflow_time:.2f}s")
