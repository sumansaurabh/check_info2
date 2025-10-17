"""
Integration tests for health check and processors endpoints
Tests basic API availability and processor discovery
"""

import pytest
import requests


class TestHealthEndpoints:
	"""Test suite for health and system status endpoints"""

	def test_root_endpoint(self, api_client: requests.Session, api_base_url: str):
		"""Test root endpoint returns basic API information"""
		response = api_client.get(f"{api_base_url}/")

		assert response.status_code == 200
		data = response.json()

		assert "message" in data
		assert "version" in data
		assert data["version"] == "3.3.0"
		assert "docs" in data
		assert "health" in data

	def test_health_check(self, api_client: requests.Session, api_base_url: str):
		"""Test health endpoint returns system status"""
		response = api_client.get(f"{api_base_url}/health")

		assert response.status_code == 200
		data = response.json()

		# Verify response structure
		assert "status" in data
		assert data["status"] == "healthy"
		assert "version" in data
		assert data["version"] == "3.3.0"
		assert "processors_available" in data

		# Verify processors list is not empty
		processors = data["processors_available"]
		assert isinstance(processors, list)
		assert len(processors) > 0

		# Verify face_swapper is available
		assert "face_swapper" in processors

		print(f"\n✓ Health check passed")
		print(f"  Available processors: {', '.join(processors)}")

	def test_list_processors(self, api_client: requests.Session, api_base_url: str):
		"""Test processors endpoint returns detailed processor information"""
		response = api_client.get(f"{api_base_url}/processors")

		assert response.status_code == 200
		processors = response.json()

		# Verify response is a list
		assert isinstance(processors, list)
		assert len(processors) > 0

		# Verify each processor has required fields
		for processor in processors:
			assert "name" in processor
			assert "available" in processor
			assert isinstance(processor["available"], bool)

		# Find face_swapper processor
		face_swapper = next((p for p in processors if p["name"] == "face_swapper"), None)
		assert face_swapper is not None, "face_swapper processor not found"

		# Report processor availability
		available_count = sum(1 for p in processors if p["available"])
		print(f"\n✓ Processors endpoint working")
		print(f"  Total processors: {len(processors)}")
		print(f"  Available: {available_count}")
		print(f"  face_swapper available: {face_swapper['available']}")

		# List all processors with status
		for processor in processors:
			status = "✓" if processor["available"] else "✗"
			print(f"  {status} {processor['name']}")

	def test_health_performance(
		self,
		api_client: requests.Session,
		api_base_url: str,
		performance_tracker
	):
		"""Benchmark health endpoint response time"""
		performance_tracker.start("health_check")

		response = api_client.get(f"{api_base_url}/health")

		duration = performance_tracker.end("health_check")

		assert response.status_code == 200
		assert duration < 5.0, f"Health check too slow: {duration:.2f}s"

		print(f"\n⏱ Health check response time: {duration:.3f}s")

	def test_openapi_docs_available(self, api_client: requests.Session, api_base_url: str):
		"""Test OpenAPI documentation is accessible"""
		# Test OpenAPI JSON
		response = api_client.get(f"{api_base_url}/openapi.json")
		assert response.status_code == 200

		openapi_spec = response.json()
		assert "openapi" in openapi_spec
		assert "info" in openapi_spec
		assert "paths" in openapi_spec

		# Verify key endpoints are documented
		paths = openapi_spec["paths"]
		assert "/health" in paths
		assert "/processors" in paths
		assert "/process/image" in paths
		assert "/process/video" in paths
		assert "/jobs/{job_id}" in paths

		print(f"\n✓ OpenAPI documentation available")
		print(f"  Documented endpoints: {len(paths)}")

		# Test Swagger UI is accessible
		response = api_client.get(f"{api_base_url}/docs")
		assert response.status_code == 200
		assert "swagger" in response.text.lower() or "redoc" in response.text.lower()

		print(f"  Swagger UI: {api_base_url}/docs")
