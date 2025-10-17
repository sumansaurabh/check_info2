# FaceFusion API Integration Tests

Comprehensive integration test suite for the FaceFusion REST API. Tests the complete face swap workflow including health checks, image/video processing, job management, and file operations.

## 🎯 Test Coverage

### Test Modules

1. **`test_health.py`** - API health and system status
   - Root endpoint
   - Health check
   - Processor listing
   - OpenAPI documentation
   - Performance benchmarks

2. **`test_image_processing.py`** - Image face swap workflow
   - Complete face swap pipeline (upload → process → poll → download)
   - Invalid input handling
   - Custom parameters
   - Performance tracking

3. **`test_video_processing.py`** - Video face swap workflow
   - Video processing with extended timeouts
   - Custom FPS and scaling
   - Error handling

4. **`test_jobs.py`** - Job management and monitoring
   - Job status retrieval
   - Job listing with filters
   - Lifecycle tracking (queued → running → completed)
   - Concurrent job handling

5. **`test_file_operations.py`** - File download and deletion
   - Output file download
   - Auto-cleanup options
   - File deletion
   - Complete workflow testing

## 🚀 Quick Start

### Prerequisites

1. **Install test dependencies:**
   ```bash
   pip install pytest requests pillow
   ```

2. **Start the FaceFusion API server:**
   ```bash
   # In one terminal
   python facefusion.py api --api-host 0.0.0.0 --api-port 8000

   # Or use the restart script
   ./run_with_restart.sh api
   ```

3. **Add test fixtures:**
   ```bash
   # Add your test images to the fixtures directory
   tests/fixtures/
   ├── source.jpg    # Face to swap FROM (person's face)
   ├── target.jpg    # Image to swap TO (target image)
   └── target.mp4    # Video to swap TO (optional for video tests)
   ```

### Running Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_health.py -v

# Run specific test
pytest tests/integration/test_image_processing.py::TestImageProcessing::test_image_face_swap_complete_workflow -v

# Run with detailed output
pytest tests/integration/ -v -s

# Run only fast tests (skip video)
pytest tests/integration/ -v -m "not slow"

# Run with performance report
pytest tests/integration/ -v --tb=short
```

## 📁 Test Fixtures

### Required Images

Place test images in `tests/fixtures/`:

- **`source.jpg`** - Source face image (512x512 or larger recommended)
  - Should contain a clear, front-facing human face
  - JPEG format recommended
  - Minimum 256x256 pixels

- **`target.jpg`** - Target image for face swapping
  - Should contain one or more faces
  - JPEG/PNG format
  - Any reasonable resolution

- **`target.mp4`** - Target video (optional, for video tests)
  - Should contain faces
  - MP4 format
  - Short duration recommended for faster tests (5-10 seconds)

### Placeholder Generation

If fixture files are missing, the tests will:
1. Create placeholder images with instructions
2. Skip tests that require those fixtures
3. Display the expected file path

## ⚙️ Configuration

### Environment Variables

```bash
# API server URL (default: http://localhost:8000)
export FACEFUSION_API_URL="http://localhost:8000"

# Custom timeouts (optional)
export API_TIMEOUT=10           # API call timeout in seconds
export JOB_POLL_TIMEOUT=60      # Job completion timeout
export JOB_POLL_INTERVAL=2      # Polling interval
```

### Test Configuration

Edit `conftest.py` to customize:

```python
API_BASE_URL = "http://localhost:8000"  # API server URL
API_TIMEOUT = 10                         # Request timeout
JOB_POLL_TIMEOUT = 60                    # Job polling timeout
JOB_POLL_INTERVAL = 2                    # Poll interval
```

## 📊 Performance Benchmarks

Tests include performance tracking for:

- **Job Submission Time**: Time to upload and queue job
- **Processing Time**: Time from queued to completed
- **Download Time**: Time to retrieve output file
- **Total Workflow Time**: End-to-end duration

### Expected Performance (CPU, inswapper_128)

- Image processing: 15-30 seconds
- Job submission: < 5 seconds
- Download: < 10 seconds
- Total workflow: 30-60 seconds

Video processing times vary by:
- Video length
- Resolution
- Frame count
- Hardware (CPU vs GPU)

## 🧪 Test Scenarios

### Success Paths
- ✅ Complete face swap workflow
- ✅ Custom parameters (FPS, scale, detector settings)
- ✅ Concurrent job processing
- ✅ File download and cleanup

### Error Handling
- ✅ Missing source image for face_swapper
- ✅ Invalid image files
- ✅ Non-existent job IDs
- ✅ Non-existent output files
- ✅ Job timeout scenarios

### Performance
- ✅ Response time benchmarks
- ✅ Job processing duration
- ✅ Download speed
- ✅ Lifecycle tracking

## 🐛 Troubleshooting

### API Server Not Reachable

```
Error: API server not reachable at http://localhost:8000
```

**Solution:**
1. Ensure API server is running: `python facefusion.py api`
2. Check the port is correct (default: 8000)
3. Verify no firewall blocking localhost connections

### Test Fixtures Missing

```
SKIPPED: Please add source face image to: tests/fixtures/source.jpg
```

**Solution:**
1. Add test images to `tests/fixtures/` directory
2. Ensure images contain clear faces
3. Check file permissions are readable

### Job Timeout

```
TimeoutError: Job did not complete within 60s
```

**Solution:**
1. Increase timeout in conftest.py: `JOB_POLL_TIMEOUT = 120`
2. Use faster execution provider (GPU if available)
3. Reduce image/video resolution for testing
4. Check API server logs for errors

### Model Not Found

```
Job failed: Model not found
```

**Solution:**
1. Ensure models are downloaded: `python facefusion.py --download`
2. Check `face_swapper_model` is set correctly
3. Use a lightweight model like `inswapper_128` for tests

## 📝 Writing New Tests

### Test Template

```python
def test_my_feature(
    self,
    api_client: requests.Session,
    api_base_url: str,
    source_image_path: Path,
    target_image_path: Path,
    performance_tracker
):
    """Test description"""
    print("\n[TEST] My feature test...")

    # Test implementation
    performance_tracker.start("my_operation")

    # Your test code here
    response = api_client.get(f"{api_base_url}/endpoint")

    duration = performance_tracker.end("my_operation")

    # Assertions
    assert response.status_code == 200
    print(f"  ✓ Test passed in {duration:.3f}s")
```

### Available Fixtures

- `api_client` - Configured requests session
- `api_base_url` - Base API URL
- `source_image_path` - Source face image
- `target_image_path` - Target image
- `target_video_path` - Target video
- `cleanup_outputs` - List for tracking files to cleanup
- `performance_tracker` - Performance measurement utility

## 🔍 Continuous Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest requests pillow

      - name: Add test fixtures
        run: |
          mkdir -p tests/fixtures
          # Add your fixture download/generation here

      - name: Start API server
        run: |
          python facefusion.py api &
          sleep 10  # Wait for server startup

      - name: Run integration tests
        run: pytest tests/integration/ -v --tb=short
```

## 📚 References

- [FaceFusion API Documentation](../API_README.md)
- [FaceFusion Main README](../README.md)
- [Pytest Documentation](https://docs.pytest.org/)
- [Requests Documentation](https://requests.readthedocs.io/)

## 🤝 Contributing

When adding new tests:
1. Follow existing test structure and naming
2. Include docstrings explaining test purpose
3. Add performance tracking for time-critical operations
4. Handle both success and failure scenarios
5. Clean up test artifacts (use `cleanup_outputs` fixture)
6. Update this README with new test coverage

## 📄 License

Same as FaceFusion main project.
