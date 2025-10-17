# How to Run Tests and View Results

## 🎯 Quick Command to See Everything

```bash
cd tests
./integration/run_tests.sh --image -v
```

This will:
- ✅ Show all print statements (progress, timing, file locations)
- ✅ Run only image processing tests (fastest to see results)
- ✅ Save generated images to `tests/integration/test_outputs/`
- ✅ Show you the exact command to view the result

## 📁 Where Are My Generated Images?

After running tests, generated images are saved to:
```
tests/integration/test_outputs/
├── result_<uuid>.jpg           # Main face swap result
└── result_custom_<uuid>.jpg    # Custom parameters result
```

## 🖼️ How to View Generated Images

### Option 1: Automatic (Recommended)
The test output will show:
```
🖼️  VIEW YOUR RESULT: open /path/to/tests/integration/test_outputs/result_xxx.jpg
```

Just copy and run that command!

### Option 2: Manual
```bash
# From tests/ directory
open integration/test_outputs/result_*.jpg

# Or on Linux
xdg-open integration/test_outputs/result_*.jpg

# Or just navigate to the folder
cd integration/test_outputs
ls -lh
```

### Option 3: In VS Code
1. Open the file explorer in VS Code
2. Navigate to `tests/integration/test_outputs/`
3. Click on any `.jpg` file to view it

## 📋 Running Tests with Full Output

### See ALL Details (Recommended)
```bash
cd tests
./integration/run_tests.sh --image -v
```

### Or use pytest directly
```bash
cd tests/integration
pytest test_image_processing.py -v -s
```

The `-s` flag is KEY - it shows all print statements!

## 🎬 Step-by-Step: First Test Run

### 1. Make sure API server is running
```bash
# Terminal 1
python facefusion.py api
```

### 2. Run the image test with verbose output
```bash
# Terminal 2
cd tests
./integration/run_tests.sh --image
```

### 3. Look for this output:
```
[1/4] Submitting face swap job...
  ✓ Job submitted: api-xxxxx
  ⏱ Submission time: 0.234s

[2/4] Polling job status (timeout: 60s)...
  [0.0s] Job api-xxxxx: queued
  [2.0s] Job api-xxxxx: running
  [15.3s] Job api-xxxxx: completed
  ✓ Job completed successfully
  ⏱ Processing time: 15.30s

[3/4] Downloading output image...
  ✓ Downloaded to: /path/to/tests/integration/test_outputs/result_xxx.jpg
  ⏱ Download time: 0.145s
  📊 File size: 145.3 KB

  🖼️  VIEW YOUR RESULT: open /path/to/tests/integration/test_outputs/result_xxx.jpg

[4/4] Verifying output image...
  ✓ Output image is valid

PERFORMANCE SUMMARY
====================================
  Job submission:  0.234s
  Job processing:  15.30s
  File download:   0.145s
  Total workflow:  15.68s
====================================
```

### 4. View your generated image
Copy the command from the output:
```bash
open /path/to/tests/integration/test_outputs/result_xxx.jpg
```

## 🚀 Different Test Modes

### Fast Health Check (5 seconds)
```bash
./integration/run_tests.sh --health
```
No images generated, just API checks

### Image Processing (30-60 seconds)
```bash
./integration/run_tests.sh --image
```
**Generates face-swapped images!** ✨

### Job Management (10-20 seconds)
```bash
./integration/run_tests.sh --jobs
```
Also generates images as side effect

### File Operations (30-60 seconds)
```bash
./integration/run_tests.sh --files
```
Tests download/delete, generates images

### Video Processing (60-120 seconds)
```bash
./integration/run_tests.sh --video
```
Requires `target.mp4` in fixtures

### All Tests (2-3 minutes)
```bash
./integration/run_tests.sh
```
Runs everything

## 🔍 Troubleshooting

### "I don't see any print output!"
**Fix:** Add `-v` or use `-s` with pytest
```bash
# Using the runner script
./integration/run_tests.sh --image -v

# Using pytest directly
cd integration
pytest test_image_processing.py -s
```

### "Where is my generated image?"
**Check:**
```bash
cd tests/integration/test_outputs
ls -lh
```

If folder doesn't exist, the test might have failed before downloading.

### "Test passed but no image"
The test might have cleaned up. Check the test output for the file path, or modify cleanup settings in conftest.py:
```python
# In conftest.py, line ~50
cleanup_outputs = []  # This tracks files to clean up
```

### "I want to keep ALL generated images"
Comment out the cleanup in conftest.py:
```python
# In conftest.py cleanup_outputs fixture
# Don't delete files:
# for file_path in output_files:
#     if Path(file_path).exists():
#         Path(file_path).unlink()
```

## 📊 Understanding the Output

### Job Status Flow
```
queued → running → completed
   ↓        ↓          ↓
  2s      15-30s    Done!
```

### Performance Metrics
- **Job submission**: Time to upload files and create job (should be < 5s)
- **Job processing**: Time for face swap (15-30s on CPU, 3-10s on GPU)
- **File download**: Time to retrieve result (should be < 10s)
- **Total workflow**: End-to-end time

## 🎨 What You'll See in Generated Images

The face swap tests will:
1. Take the face from `source.jpg`
2. Swap it onto faces in `target.jpg`
3. Save the result to `test_outputs/`

The result shows the target image with the source face swapped in!

## 💡 Pro Tips

1. **Always use `-v` for verbose output**
   ```bash
   ./integration/run_tests.sh --image -v
   ```

2. **View images immediately**
   ```bash
   # On macOS
   open tests/integration/test_outputs/*.jpg

   # On Linux
   xdg-open tests/integration/test_outputs/*.jpg
   ```

3. **Keep test outputs**
   Don't worry about cleanup - images are saved before cleanup happens!

4. **Compare results**
   Run tests multiple times and compare:
   ```bash
   ls -lt tests/integration/test_outputs/
   ```

5. **Use real face images**
   Replace placeholders for better results:
   ```bash
   cp your_photo.jpg tests/fixtures/source.jpg
   cp group_photo.jpg tests/fixtures/target.jpg
   ```

## 🎯 Recommended First Run

```bash
# 1. Start API server
python facefusion.py api

# 2. In another terminal
cd tests

# 3. Run image tests with full output
./integration/run_tests.sh --image -v

# 4. Look for the "VIEW YOUR RESULT" line and copy that command

# 5. View your generated image!
```

## 📸 Example Session

```bash
$ cd tests
$ ./integration/run_tests.sh --image -v

========================================
FaceFusion API Integration Test Runner
========================================
✓ pytest found
✓ API server is running at http://localhost:8000
✓ All required fixtures present

Running tests...
Mode: Image processing tests

test_image_processing.py::TestImageProcessing::test_image_face_swap_complete_workflow

============================================================
FACE SWAP IMAGE PROCESSING TEST
============================================================

[1/4] Submitting face swap job...
  ✓ Job submitted: api-20251017-123456
  ⏱ Submission time: 0.234s

[2/4] Polling job status (timeout: 60s)...
  [0.0s] Job api-20251017-123456: queued
  [2.0s] Job api-20251017-123456: running
  [18.5s] Job api-20251017-123456: completed
  ✓ Job completed successfully
  ⏱ Processing time: 18.50s
  📁 Output path: .api_outputs/abc123.jpg

[3/4] Downloading output image...
  ✓ Downloaded to: /path/to/tests/integration/test_outputs/result_abc123.jpg
  ⏱ Download time: 0.145s
  📊 File size: 145.3 KB

  🖼️  VIEW YOUR RESULT: open /path/to/tests/integration/test_outputs/result_abc123.jpg

[4/4] Verifying output image...
  ✓ Output image is valid

============================================================
PERFORMANCE SUMMARY
============================================================
  Job submission:  0.234s
  Job processing:  18.50s
  File download:   0.145s
  Total workflow:  18.88s
============================================================

PASSED

========================================
✓ All tests passed!
========================================
```

Now just run the command shown:
```bash
open /path/to/tests/integration/test_outputs/result_abc123.jpg
```

And you'll see your face-swapped image! 🎉

---

**Key Takeaway:** Always use `-v` flag to see detailed output and file locations!
