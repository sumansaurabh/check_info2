# FaceFusion: Network Access & API Setup Summary

## What Was Implemented

### 1. Network Binding (0.0.0.0)
✅ **Updated Gradio UI** to listen on all network interfaces
- File: `facefusion/uis/layouts/default.py`
- Server binds to `0.0.0.0:7860`
- Accessible from any machine on your network

### 2. Auto-Restart Script
✅ **Created `run_with_restart.sh`**
- Automatic restart on crashes
- Timestamped logging to `./logs/`
- Configurable retry delays
- Graceful shutdown handling
- Works with all commands: `run`, `api`, `headless-run`, etc.

### 3. REST API Server
✅ **New FastAPI-based API** (`facefusion/api_server.py`)
- OpenAPI-compliant endpoints
- Interactive docs at `/docs`
- Process images and videos programmatically
- File upload/download support
- CORS enabled for external access

## Quick Start

### On Ubuntu Server

1. **Pull latest changes:**
```bash
git pull
conda activate facefusion
pip install fastapi uvicorn python-multipart
```

2. **Start Gradio UI (with auto-restart):**
```bash
./run_with_restart.sh run
```
Access at: `http://129.146.117.178:7860`

3. **Start REST API (with auto-restart):**
```bash
./run_with_restart.sh api
```
Access at: `http://129.146.117.178:8000`
API Docs: `http://129.146.117.178:8000/docs`

### From Your Mac

**Option 1: SSH Port Forwarding (Recommended)**
```bash
# For Gradio UI
ssh -L 7860:localhost:7860 ubuntu@129.146.117.178

# For REST API
ssh -L 8000:localhost:8000 ubuntu@129.146.117.178

# Both at once
ssh -L 7860:localhost:7860 -L 8000:localhost:8000 ubuntu@129.146.117.178
```

Then access:
- UI: http://localhost:7860
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Option 2: Direct Access (if firewall allows)**
- UI: http://129.146.117.178:7860
- API: http://129.146.117.178:8000

## API Usage Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Process Image
```bash
curl -X POST "http://localhost:8000/process/image" \
  -F "target=@image.jpg" \
  -F "source=@face.jpg" \
  -F 'request={"processors":["face_swapper"],"execution_providers":["cpu"]}'
```

### Python Client
```python
import requests

files = {
    "target": open("target.jpg", "rb"),
    "source": open("source.jpg", "rb")
}
data = {
    "request": '{"processors":["face_swapper"]}'
}

response = requests.post("http://localhost:8000/process/image",
                        files=files, data=data)
result = response.json()
print(result)
```

## Background Execution

### Using Screen
```bash
# Start UI
screen -dmS ui ./run_with_restart.sh run

# Start API
screen -dmS api ./run_with_restart.sh api

# List sessions
screen -ls

# Attach to session
screen -r ui  # or screen -r api

# Detach: Ctrl+A then D
```

### Using Nohup
```bash
# Start in background
nohup ./run_with_restart.sh run > /dev/null 2>&1 &
nohup ./run_with_restart.sh api > /dev/null 2>&1 &

# Check logs
tail -f logs/facefusion_*.log
```

## Files Modified/Created

### Modified:
- `facefusion/core.py` - Added `api` command route
- `facefusion/program.py` - Added `api` subcommand
- `facefusion/uis/layouts/default.py` - Listen on 0.0.0.0:7860
- `requirements.txt` - Added fastapi, uvicorn, python-multipart

### Created:
- `facefusion/api_server.py` - FastAPI REST API server
- `run_with_restart.sh` - Auto-restart wrapper script
- `API_README.md` - Complete API documentation
- `RESTART_README.md` - Auto-restart documentation
- `SUMMARY.md` - This file

## Port Summary
- **7860**: Gradio Web UI
- **8000**: REST API Server

## Next Steps

1. Pull changes on server: `git pull`
2. Install dependencies: `pip install -r requirements.txt`
3. Test UI: `./run_with_restart.sh run`
4. Test API: `./run_with_restart.sh api`
5. Set up SSH tunnels from Mac
6. Test API endpoints with curl or Python

## Documentation
- Full API docs: `API_README.md`
- Auto-restart docs: `RESTART_README.md`
- Interactive API docs: http://localhost:8000/docs (when running)

## Security Notes
- Binding to 0.0.0.0 exposes services to your network
- Use SSH tunnels for secure remote access
- Consider adding authentication for production use
- Use firewall rules to restrict access if needed
