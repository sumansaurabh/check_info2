# FaceFusion API Integration Tests

## 📚 Quick Navigation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 3 steps
- **[README.md](README.md)** - Complete documentation
- **[SUMMARY.md](SUMMARY.md)** - What was built and why

## 🚀 TL;DR

```bash
# 1. Install
pip install pytest requests pillow

# 2. Add test images
cp your_face.jpg ../fixtures/source.jpg
cp target.jpg ../fixtures/target.jpg

# 3. Run
./run_tests.sh
```

## 📊 Test Suite

**24 Integration Tests** across 5 test files:

| File | Tests | Focus |
|------|-------|-------|
| `test_health.py` | 5 | API health & processors |
| `test_image_processing.py` | 4 | Image face swap |
| `test_video_processing.py` | 3 | Video face swap |
| `test_jobs.py` | 6 | Job management |
| `test_file_operations.py` | 6 | Downloads & cleanup |

## 🎯 Key Features

✅ Real integration tests (not mocked)  
✅ Complete face swap workflows  
✅ Performance benchmarks built-in  
✅ Automatic cleanup  
✅ Rich terminal output  
✅ Production-ready  

## 📖 Documentation

- **Installation**: See [README.md](README.md#-quick-start)
- **Configuration**: See [README.md](README.md#-configuration)
- **Troubleshooting**: See [README.md](README.md#-troubleshooting)
- **Examples**: See [QUICKSTART.md](QUICKSTART.md#-test-commands)

## 🔗 API Server

Make sure the API server is running:
```bash
python facefusion.py api --api-host 0.0.0.0 --api-port 8000
```

## 📝 Files

```
integration/
├── conftest.py              # Test fixtures & helpers
├── test_health.py           # Health & processor tests
├── test_image_processing.py # Image face swap tests  
├── test_video_processing.py # Video face swap tests
├── test_jobs.py             # Job management tests
├── test_file_operations.py  # File operation tests
├── pytest.ini               # Pytest configuration
├── run_tests.sh            # Test runner script
├── requirements-test.txt    # Python dependencies
├── README.md                # Full documentation
├── QUICKSTART.md            # Quick reference
├── SUMMARY.md               # Project summary
└── INDEX.md                 # This file

../fixtures/
├── source.jpg               # Source face image
├── target.jpg               # Target image
└── create_placeholders.py   # Placeholder generator
```

## 💡 Quick Commands

```bash
# Run all tests
./run_tests.sh

# Run specific suite
./run_tests.sh --health
./run_tests.sh --image
./run_tests.sh --jobs

# Using pytest directly
pytest -v                    # All tests
pytest test_health.py -v     # One file
pytest -v -s                 # With output
pytest -x                    # Stop on failure
```

## 🎓 Learn More

For complete information, see:
- [README.md](README.md) - Comprehensive guide
- [QUICKSTART.md](QUICKSTART.md) - Quick reference
- [SUMMARY.md](SUMMARY.md) - Project overview

---

**FaceFusion API v3.3.0** | **24 Tests** | **pytest Framework**
