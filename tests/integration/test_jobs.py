"""
Integration tests for job management endpoints
Tests job listing, status retrieval, and monitoring
"""

import requests


class TestJobManagement:
	"""Test suite for job management and monitoring"""

	def test_get_job_status_valid(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path,
		target_image_path
	):
		"""Test retrieving status of a valid job"""
		print("\n[TEST] Get job status for valid job...")

		# First create a job
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

		assert response.status_code == 202
		job_id = response.json()["job_id"]

		# Now test getting job status
		response = api_client.get(f"{api_base_url}/jobs/{job_id}")

		assert response.status_code == 200
		job_status = response.json()

		assert "job_id" in job_status
		assert job_status["job_id"] == job_id
		assert "status" in job_status
		assert job_status["status"] in ["queued", "running", "completed", "failed"]

		print(f"  ✓ Job status retrieved: {job_status['status']}")
		print(f"    Job ID: {job_id}")
		if job_status.get("output_path"):
			print(f"    Output: {job_status['output_path']}")

	def test_get_job_status_invalid(
		self,
		api_client: requests.Session,
		api_base_url: str
	):
		"""Test retrieving status of non-existent job"""
		print("\n[TEST] Get job status for invalid job ID...")

		fake_job_id = "nonexistent-job-12345"
		response = api_client.get(f"{api_base_url}/jobs/{fake_job_id}")

		assert response.status_code == 404
		error = response.json()
		assert "detail" in error
		assert "not found" in error["detail"].lower()

		print(f"  ✓ Correctly returned 404 for invalid job ID")

	def test_list_jobs(
		self,
		api_client: requests.Session,
		api_base_url: str
	):
		"""Test listing all jobs"""
		print("\n[TEST] List all jobs...")

		response = api_client.get(f"{api_base_url}/jobs")

		assert response.status_code == 200
		jobs = response.json()

		assert isinstance(jobs, list)

		print(f"  ✓ Retrieved {len(jobs)} jobs")

		# Verify job structure
		if len(jobs) > 0:
			job = jobs[0]
			assert "job_id" in job
			assert "status" in job

			print(f"    Latest job: {job['job_id']} - {job['status']}")

			# Count by status
			status_counts = {}
			for job in jobs:
				status = job["status"]
				status_counts[status] = status_counts.get(status, 0) + 1

			print(f"    Status breakdown:")
			for status, count in sorted(status_counts.items()):
				print(f"      {status}: {count}")

	def test_list_jobs_with_limit(
		self,
		api_client: requests.Session,
		api_base_url: str
	):
		"""Test listing jobs with limit parameter"""
		print("\n[TEST] List jobs with limit=5...")

		response = api_client.get(
			f"{api_base_url}/jobs",
			params={"limit": 5}
		)

		assert response.status_code == 200
		jobs = response.json()

		assert isinstance(jobs, list)
		assert len(jobs) <= 5

		print(f"  ✓ Retrieved {len(jobs)} jobs (limit: 5)")

	def test_job_lifecycle_tracking(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path,
		target_image_path,
		performance_tracker
	):
		"""
		Test complete job lifecycle:
		queued -> running -> completed
		"""
		print("\n[TEST] Track job lifecycle from queued to completed...")

		# Submit job
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

		# Track status transitions
		import time
		statuses_seen = []
		max_checks = 30

		performance_tracker.start("lifecycle_tracking")

		for i in range(max_checks):
			response = api_client.get(f"{api_base_url}/jobs/{job_id}")
			job_status = response.json()
			current_status = job_status["status"]

			if not statuses_seen or statuses_seen[-1] != current_status:
				statuses_seen.append(current_status)
				print(f"  [{i*2}s] Status: {current_status}")

			if current_status in ["completed", "failed"]:
				break

			time.sleep(2)

		tracking_time = performance_tracker.end("lifecycle_tracking")

		# Verify we saw expected transitions
		assert "queued" in statuses_seen or "running" in statuses_seen, \
			"Expected to see queued or running status"
		assert statuses_seen[-1] in ["completed", "failed"], \
			"Expected final status to be completed or failed"

		print(f"\n  ✓ Job lifecycle tracked successfully")
		print(f"    Transitions: {' -> '.join(statuses_seen)}")
		print(f"    Total time: {tracking_time:.2f}s")

	def test_concurrent_jobs(
		self,
		api_client: requests.Session,
		api_base_url: str,
		source_image_path,
		target_image_path
	):
		"""Test submitting multiple jobs concurrently"""
		print("\n[TEST] Submit 3 concurrent jobs...")

		job_ids = []

		# Submit 3 jobs
		for i in range(3):
			with open(source_image_path, 'rb') as source_file, \
			     open(target_image_path, 'rb') as target_file:

				files = {
					'source': (f'source_{i}.jpg', source_file, 'image/jpeg'),
					'target': (f'target_{i}.jpg', target_file, 'image/jpeg')
				}

				response = api_client.post(
					f"{api_base_url}/process/image",
					files=files,
					timeout=30
				)

			assert response.status_code == 202
			job_id = response.json()["job_id"]
			job_ids.append(job_id)
			print(f"  ✓ Job {i+1} submitted: {job_id}")

		# Verify all jobs are tracked
		response = api_client.get(f"{api_base_url}/jobs")
		all_jobs = response.json()
		all_job_ids = [job["job_id"] for job in all_jobs]

		for job_id in job_ids:
			assert job_id in all_job_ids, f"Job {job_id} not found in job list"

		print(f"\n  ✓ All {len(job_ids)} concurrent jobs tracked successfully")
