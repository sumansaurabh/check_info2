# FaceFusion Auto-Restart Script

## Overview
This directory contains `run_with_restart.sh`, a bash wrapper that automatically restarts FaceFusion if it crashes.

## Changes Made

### 1. Gradio Network Binding
Updated `facefusion/uis/layouts/default.py` to listen on all network interfaces:
- **server_name**: `0.0.0.0` (instead of default localhost)
- **server_port**: `7860`

This allows remote access from other machines on your network.

### 2. Auto-Restart Script
Created `run_with_restart.sh` with features:
- Automatic restart on crash (unlimited retries by default)
- Timestamped logging to `./logs/` directory
- Configurable retry delay (5 seconds default)
- Graceful shutdown handling (SIGTERM/SIGINT)
- Optional maximum retry limit

## Usage

### Basic Usage
```bash
# Make executable (already done)
chmod +x run_with_restart.sh

# Run with auto-restart
./run_with_restart.sh run

# Run with browser auto-open
./run_with_restart.sh run --open-browser

# Run headless
./run_with_restart.sh headless-run
```

### Configuration
Edit these variables at the top of `run_with_restart.sh`:
```bash
MAX_RETRIES=0           # 0 = unlimited, or set a number
RETRY_DELAY=5           # seconds between restarts
LOG_DIR="./logs"        # where to store logs
```

### Access the UI
After starting with the updated configuration:
- **Locally on server**: http://localhost:7860
- **From your Mac** (via SSH tunnel):
  ```bash
  ssh -L 7860:localhost:7860 ubuntu@129.146.117.178
  ```
  Then open: http://localhost:7860

- **Directly from network** (if firewall allows):
  ```
  http://129.146.117.178:7860
  ```

### Logs
All output is saved to timestamped files in `./logs/`:
```bash
# View latest log
tail -f logs/facefusion_*.log

# View all logs
ls -lh logs/
```

### Stopping the Service
Press `Ctrl+C` to gracefully stop. The script will:
1. Send SIGTERM to the FaceFusion process
2. Wait for clean shutdown
3. Exit without restarting

### Running in Background
To run detached (survives terminal disconnect):
```bash
nohup ./run_with_restart.sh run > /dev/null 2>&1 &

# Or use screen/tmux
screen -S facefusion
./run_with_restart.sh run
# Press Ctrl+A, then D to detach
```

### Systemd Service (Optional)
For production deployment on Ubuntu, create `/etc/systemd/system/facefusion.service`:
```ini
[Unit]
Description=FaceFusion with Auto-Restart
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/miniconda3/grumpy/check_info2
ExecStart=/home/ubuntu/miniconda3/grumpy/check_info2/run_with_restart.sh run
Restart=always
RestartSec=10
StandardOutput=append:/var/log/facefusion.log
StandardError=append:/var/log/facefusion.log

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable facefusion
sudo systemctl start facefusion
sudo systemctl status facefusion
```

## Security Notes
- Binding to `0.0.0.0` exposes the service to your network
- Consider adding authentication if exposing publicly
- Use firewall rules to restrict access if needed
- For public internet access, use a reverse proxy (nginx) with HTTPS

## Troubleshooting
- **Port already in use**: Change `server_port` in `default.py` or kill existing process
- **Permission denied**: Ensure script is executable (`chmod +x`)
- **Module not found**: Activate the conda environment first:
  ```bash
  conda activate facefusion
  ./run_with_restart.sh run
  ```
