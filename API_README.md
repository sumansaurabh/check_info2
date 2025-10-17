# FaceFusion REST API Documentation

## Overview
FaceFusion now includes a FastAPI-based REST API server for external service integration. The API provides OpenAPI-compliant endpoints for programmatic access to face processing operations.

## Installation

Install additional API dependencies:
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install fastapi uvicorn python-multipart
```

## Starting the API Server

### Basic Usage
```bash
# Start API server on default port 8000
python facefusion.py api

# Or with auto-restart wrapper
./run_with_restart.sh api
```

The API server will:
- Listen on `0.0.0.0:8000` (all network interfaces)
- Generate interactive API docs at http://localhost:8000/docs
- Provide OpenAPI schema at http://localhost:8000/openapi.json

### Accessing from Your Mac
```bash
# SSH tunnel
ssh -L 8000:localhost:8000 ubuntu@129.146.117.178
```
Then open: http://localhost:8000/docs

## API Endpoints

### Health Check
```bash
# Check API status
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "3.3.0",
  "processors_available": ["face_swapper", "face_enhancer", ...]
}
```

### List Processors
```bash
# Get available processors
curl http://localhost:8000/processors
```

Response:
```json
[
  {"name": "face_swapper", "available": true},
  {"name": "face_enhancer", "available": true},
  ...
]
```

### Process Image
```bash
# Face swap example
curl -X POST "http://localhost:8000/process/image" \
  -F "target=@target_image.jpg" \
  -F "source=@source_face.jpg" \
  -F 'request={"processors":["face_swapper"],"execution_providers":["cpu"]}'
```

Response:
```json
{
  "job_id": "api_20250101_120000_abc123",
  "status": "completed",
  "output_path": ".api_outputs/550e8400-e29b-41d4-a716-446655440000.jpg"
}
```

### Process Video
```bash
# Face swap in video
curl -X POST "http://localhost:8000/process/video" \
  -F "target=@target_video.mp4" \
  -F "source=@source_face.jpg" \
  -F 'request={"processors":["face_swapper"],"execution_providers":["cpu"],"execution_thread_count":4}'
```

### Download Output
```bash
# Download processed file
curl -O -J "http://localhost:8000/download/output_filename.jpg"

# Download and auto-delete
curl -O -J "http://localhost:8000/download/output_filename.jpg?cleanup=true"
```

### Delete Output
```bash
# Manually delete output file
curl -X DELETE "http://localhost:8000/output/output_filename.jpg"
```

## Request Parameters

### ProcessRequest Schema
```json
{
  "processors": ["face_swapper"],           // List of processors to apply
  "execution_providers": ["cpu"],           // cpu, cuda, coreml, etc.
  "execution_thread_count": 1,             // 1-32 threads
  "output_video_fps": null,                // Output FPS (null = same as input)
  "output_image_scale": 100,               // 10-400%
  "output_video_scale": 100,               // 10-400%
  "face_detector_model": "yoloface_8n",    // Face detection model
  "face_detector_score": 0.5               // Detection threshold (0.0-1.0)
}
```

## Python Client Example

```python
import requests

# API endpoint
API_URL = "http://localhost:8000"

# Process image
with open("target.jpg", "rb") as target_file, \
     open("source.jpg", "rb") as source_file:

    files = {
        "target": target_file,
        "source": source_file
    }

    data = {
        "request": '{"processors":["face_swapper"],"execution_providers":["cpu"]}'
    }

    response = requests.post(f"{API_URL}/process/image", files=files, data=data)
    result = response.json()

    print(f"Job ID: {result['job_id']}")
    print(f"Status: {result['status']}")

    if result['status'] == 'completed':
        # Download result
        output_filename = result['output_path'].split('/')[-1]
        output_response = requests.get(f"{API_URL}/download/{output_filename}")

        with open("result.jpg", "wb") as f:
            f.write(output_response.content)

        print("Result saved to result.jpg")
```

## JavaScript/Node.js Client Example

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const API_URL = 'http://localhost:8000';

async function processImage() {
    const form = new FormData();
    form.append('target', fs.createReadStream('target.jpg'));
    form.append('source', fs.createReadStream('source.jpg'));
    form.append('request', JSON.stringify({
        processors: ['face_swapper'],
        execution_providers: ['cpu']
    }));

    const response = await axios.post(`${API_URL}/process/image`, form, {
        headers: form.getHeaders()
    });

    console.log('Job ID:', response.data.job_id);
    console.log('Status:', response.data.status);

    if (response.data.status === 'completed') {
        const filename = response.data.output_path.split('/').pop();
        const output = await axios.get(`${API_URL}/download/${filename}`, {
            responseType: 'arraybuffer'
        });

        fs.writeFileSync('result.jpg', output.data);
        console.log('Result saved to result.jpg');
    }
}

processImage().catch(console.error);
```

## Advanced Usage

### Multiple Processors
```bash
curl -X POST "http://localhost:8000/process/image" \
  -F "target=@target.jpg" \
  -F 'request={"processors":["face_swapper","face_enhancer"],"execution_providers":["cpu"]}'
```

### GPU Acceleration
```bash
curl -X POST "http://localhost:8000/process/image" \
  -F "target=@target.jpg" \
  -F "source=@source.jpg" \
  -F 'request={"processors":["face_swapper"],"execution_providers":["cuda"],"execution_thread_count":4}'
```

### High-Quality Output
```bash
curl -X POST "http://localhost:8000/process/video" \
  -F "target=@video.mp4" \
  -F "source=@face.jpg" \
  -F 'request={
    "processors":["face_swapper","face_enhancer"],
    "execution_providers":["cuda"],
    "execution_thread_count":8,
    "output_video_fps":30,
    "output_video_scale":100,
    "face_detector_score":0.6
  }'
```

## Running Both UI and API

### Option 1: Separate Processes
```bash
# Terminal 1: Gradio UI on port 7860
./run_with_restart.sh run

# Terminal 2: API on port 8000
./run_with_restart.sh api
```

### Option 2: Screen/Tmux
```bash
# Start UI in background
screen -dmS facefusion-ui ./run_with_restart.sh run

# Start API in background
screen -dmS facefusion-api ./run_with_restart.sh api

# View sessions
screen -ls

# Attach to a session
screen -r facefusion-ui
```

## Production Deployment

### Systemd Services
Create `/etc/systemd/system/facefusion-api.service`:
```ini
[Unit]
Description=FaceFusion REST API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/miniconda3/grumpy/check_info2
ExecStart=/home/ubuntu/miniconda3/grumpy/check_info2/run_with_restart.sh api
Restart=always
RestartSec=10
StandardOutput=append:/var/log/facefusion-api.log
StandardError=append:/var/log/facefusion-api.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable facefusion-api
sudo systemctl start facefusion-api
sudo systemctl status facefusion-api
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Increase timeouts for video processing
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;

        # Increase body size for file uploads
        client_max_body_size 500M;
    }
}
```

## Security Considerations

1. **Authentication**: Add API key authentication in production
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **File Size Limits**: Default max upload is 500MB (configurable)
4. **CORS**: Configure `allow_origins` appropriately for production
5. **HTTPS**: Use HTTPS in production (via reverse proxy)
6. **Firewall**: Restrict API access to trusted IPs if possible

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Upload Errors
- Check `client_max_body_size` in nginx
- Verify file permissions on upload directory
- Check available disk space

### Processing Errors
- Verify models are downloaded: `python facefusion.py force-download`
- Check execution providers: CUDA requires GPU drivers
- Monitor logs in `.api_uploads` and `.api_outputs` directories

## Interactive Documentation

Once the API server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

The interactive docs allow you to:
- Test endpoints directly from the browser
- View request/response schemas
- Download OpenAPI specifications
- Generate client SDKs

## Webhook Integration (Future)

For long-running video processing, consider implementing webhooks:
```python
# Coming soon: async processing with callbacks
{
  "webhook_url": "https://your-service.com/callback",
  "processors": ["face_swapper"],
  ...
}
```
