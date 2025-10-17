FaceFusion
==========

> Industry leading face manipulation platform.

[![Build Status](https://img.shields.io/github/actions/workflow/status/facefusion/facefusion/ci.yml.svg?branch=master)](https://github.com/facefusion/facefusion/actions?query=workflow:ci)
[![Coverage Status](https://img.shields.io/coveralls/facefusion/facefusion.svg)](https://coveralls.io/r/facefusion/facefusion)
![License](https://img.shields.io/badge/license-OpenRAIL--AS-green)


Preview
-------

![Preview](https://raw.githubusercontent.com/facefusion/facefusion/master/.github/preview.png?sanitize=true)


Installation
------------

Be aware, the [installation](https://docs.facefusion.io/installation) needs technical skills and is not recommended for beginners. In case you are not comfortable using a terminal, our [Windows Installer](http://windows-installer.facefusion.io) and [macOS Installer](http://macos-installer.facefusion.io) get you started.

### Quick Installation

```bash
# Clone repository
git clone https://github.com/facefusion/facefusion
cd facefusion

# Install with CUDA support (recommended for NVIDIA GPUs)
python install.py --onnxruntime cuda

# Or install CPU-only version
python install.py --onnxruntime default
```

### Update Existing Installation

```bash
git pull
pip install -r requirements.txt
```


Usage
-----

### Web Interface (Gradio UI)

Start the web interface:

```bash
python facefusion.py run
```

Access at: `http://localhost:7860`

### REST API Server

Start the REST API server for programmatic access:

```bash
python facefusion.py api
```

Access at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

See [API_README.md](API_README.md) for complete API documentation and examples.

### Auto-Restart Wrapper

Use the auto-restart script for production deployments (automatically restarts on crashes):

```bash
# Start Gradio UI with auto-restart
./run_with_restart.sh run

# Start REST API with auto-restart
./run_with_restart.sh api

# Logs are saved to ./logs/ directory
tail -f logs/facefusion_*.log
```

See [RESTART_README.md](RESTART_README.md) for configuration options.

### Remote Access via SSH Tunnel

Access from a remote machine using SSH port forwarding:

```bash
# Forward both UI and API ports
ssh -L 7860:localhost:7860 -L 8000:localhost:8000 user@server-ip

# Then access locally at:
# - UI: http://localhost:7860
# - API: http://localhost:8000
```

### Command Line Interface

Run the command:

```
python facefusion.py [commands] [options]

options:
  -h, --help                                      show this help message and exit
  -v, --version                                   show program's version number and exit

commands:
    run                                           run the program (Gradio UI)
    api                                           run the REST API server
    headless-run                                  run the program in headless mode
    batch-run                                     run the program in batch mode
    force-download                                force automate downloads and exit
    benchmark                                     benchmark the program
    job-list                                      list jobs by status
    job-create                                    create a drafted job
    job-submit                                    submit a drafted job to become a queued job
    job-submit-all                                submit all drafted jobs to become a queued jobs
    job-delete                                    delete a drafted, queued, failed or completed job
    job-delete-all                                delete all drafted, queued, failed and completed jobs
    job-add-step                                  add a step to a drafted job
    job-remix-step                                remix a previous step from a drafted job
    job-insert-step                               insert a step to a drafted job
    job-remove-step                               remove a step from a drafted job
    job-run                                       run a queued job
    job-run-all                                   run all queued jobs
    job-retry                                     retry a failed job
    job-retry-all                                 retry all failed jobs
```


Features
--------

### 🌐 Network Access
- Gradio UI binds to `0.0.0.0:7860` (accessible from any network interface)
- REST API binds to `0.0.0.0:8000`
- Secure remote access via SSH tunneling

### 🚀 REST API
- OpenAPI-compliant REST API for external service integration
- Process images and videos programmatically
- Upload/download files via API
- Interactive API documentation at `/docs`
- See [API_README.md](API_README.md) for examples

### 🔄 Auto-Restart
- Automatic restart on crashes
- Configurable retry delays
- Timestamped logging
- Graceful shutdown handling
- See [RESTART_README.md](RESTART_README.md) for details

### 🎨 Face Processing
- Face swapping
- Face enhancement
- Expression restoration
- Lip syncing
- Frame colorization
- And many more processors...


Documentation
-------------

- **Main Documentation**: [docs.facefusion.io](https://docs.facefusion.io)
- **API Documentation**: [API_README.md](API_README.md)
- **Auto-Restart Guide**: [RESTART_README.md](RESTART_README.md)
- **Quick Start**: [SUMMARY.md](SUMMARY.md)
