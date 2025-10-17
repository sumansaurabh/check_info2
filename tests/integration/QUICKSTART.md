# Integration Tests - Quick Reference

## 🚀 Quick Start (3 Steps)

### 1. Install Dependencies
```bash
pip install pytest requests pillow
```

### 2. Add Test Images
```bash
# Replace placeholder images with real face images
cp /path/to/your/face.jpg tests/fixtures/source.jpg
cp /path/to/target/image.jpg tests/fixtures/target.jpg
```

### 3. Run Tests
```bash
# Start API server in one terminal
python facefusion.py api --api-host 0.0.0.0 --api-port 8000

# Run tests in another terminal
cd tests
./integration/run_tests.sh
```

## 📝 Test Commands

### Run Specific Test Suites
```bash
# Health checks only (fastest)
./integration/run_tests.sh --health

# Image processing tests
./integration/run_tests.sh --image

# Job management tests
./integration/run_tests.sh --jobs

# File operations tests
./integration/run_tests.sh --files

# Video processing (requires target.mp4)
./integration/run_tests.sh --video
```

### Using pytest Directly
```bash
cd tests/integration

# All tests with verbose output
pytest -v -s

# Specific test file
pytest test_health.py -v

# Specific test
pytest test_image_processing.py::TestImageProcessing::test_image_face_swap_complete_workflow -v

# Show print statements
pytest -v -s

# Stop on first failure
pytest -x
```

## 🎯 Test Coverage

| Test File | Endpoints Tested | Time |
|-----------|-----------------|------|
| `test_health.py` | `/`, `/health`, `/processors`, `/docs` | ~5s |
| `test_image_processing.py` | `/process/image` | ~30-60s |
| `test_jobs.py` | `/jobs`, `/jobs/{id}` | ~10-20s |
| `test_file_operations.py` | `/download/{file}`, `/output/{file}` | ~30-60s |
| `test_video_processing.py` | `/process/video` | ~60-120s |

## 🐛 Common Issues

### API Server Not Running
```bash
# Error: API server not reachable
# Fix: Start the server
python facefusion.py api
```

### Missing Fixtures
```bash
# Error: SKIPPED: Please add source face image
# Fix: Add real images
cp your_face.jpg tests/fixtures/source.jpg
cp target_image.jpg tests/fixtures/target.jpg
```

### Pytest Plugin Error
```bash
# Error: ImportError: cannot import name 'call_runtest_hook'
# Fix: Already fixed in pytest.ini with -p no:flaky
```

### Job Timeout
```bash
# Error: TimeoutError: Job did not complete within 60s
# Fix: Edit conftest.py and increase JOB_POLL_TIMEOUT
```

## 📊 Performance Expectations

### CPU Processing
- Image face swap: 15-30 seconds
- Job submission: < 5 seconds
- Download: < 10 seconds

### GPU Processing (CUDA)
- Image face swap: 3-10 seconds
- Much faster overall

## 🔧 Configuration

### Environment Variables
```bash
# Custom API URL
export FACEFUSION_API_URL="http://localhost:8000"

# Custom timeouts (edit conftest.py)
API_TIMEOUT = 10           # Request timeout
JOB_POLL_TIMEOUT = 60      # Job completion timeout
JOB_POLL_INTERVAL = 2      # Poll interval
```

### Test Markers (Future)
```bash
# Fast tests only
pytest -m fast

# Slow tests only
pytest -m slow

# Smoke tests
pytest -m smoke
```

## 📁 Project Structure
```
tests/
├── integration/
│   ├── conftest.py                    # Test fixtures & helpers
│   ├── test_health.py                 # Health & processor tests
│   ├── test_image_processing.py       # Image face swap tests
│   ├── test_video_processing.py       # Video face swap tests
│   ├── test_jobs.py                   # Job management tests
│   ├── test_file_operations.py        # Download/delete tests
│   ├── pytest.ini                     # Pytest configuration
│   ├── run_tests.sh                   # Test runner script
│   └── README.md                      # Full documentation
└── fixtures/
    ├── source.jpg                     # Source face image
    ├── target.jpg                     # Target image
    ├── target.mp4                     # Target video (optional)
    └── create_placeholders.py         # Placeholder generator
```

## 💡 Tips

1. **Start Small**: Run `--health` tests first to verify setup
2. **Use Verbose Mode**: Add `-v -s` to see detailed output
3. **Watch Logs**: Monitor API server logs in another terminal
4. **Fast Iteration**: Use `--image` for quick face swap testing
5. **Real Images**: Use actual face photos for meaningful tests

## 📚 Full Documentation

See `tests/integration/README.md` for complete documentation.
