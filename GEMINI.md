# FaceFusion

## Project Overview

FaceFusion is an industry-leading, open-source face manipulation platform built in Python. It provides a versatile and powerful set of tools for face swapping, enhancement, and manipulation in both images and videos. The project is designed to be accessible through multiple interfaces, including a command-line interface (CLI), a user-friendly web interface, and a comprehensive REST API.

The core of FaceFusion's functionality is powered by the ONNX Runtime, which allows for efficient, cross-platform execution of deep learning models. This enables the use of various hardware acceleration options, such as CUDA for NVIDIA GPUs and ROCm for AMD GPUs, to significantly speed up processing.

The application is structured into several key components:

- **`facefusion/core.py`**: The main entry point of the application, responsible for parsing command-line arguments, initializing the application, and orchestrating the different processing pipelines.
- **`facefusion/processors`**: A modular system that contains the different face manipulation tools, such as face swapping, face enhancement, and lip syncing.
- **`facefusion/uis`**: The web interface, built with Gradio, which provides a graphical user interface for easy interaction with the application's features.
- **`facefusion/api_server.py`**: A REST API server built with FastAPI, which allows for programmatic integration of FaceFusion's capabilities into other applications and services.

## Building and Running

### Installation

The project uses a custom installer script to handle the installation of its dependencies. The installer can be run with the following command:

```bash
python install.py --onnxruntime <backend>
```

The `<backend>` argument specifies the ONNX Runtime backend to use for hardware acceleration. The available options are:

- `default`: CPU-only
- `cuda`: NVIDIA CUDA
- `rocm`: AMD ROCm
- `directml`: DirectML on Windows
- `openvino`: Intel OpenVINO

### Running the Application

FaceFusion can be run in several modes:

- **Web Interface:**
  ```bash
  python facefusion.py run
  ```
  This will start the Gradio web interface, which is accessible at `http://localhost:7860`.

- **REST API Server:**
  ```bash
  python facefusion.py api
  ```
  This will start the FastAPI server, which is accessible at `http://localhost:8000`. The API documentation is available at `http://localhost:8000/docs`.

- **Command-Line Interface:**
  ```bash
  python facefusion.py [command] [options]
  ```
  The CLI provides a wide range of commands for processing images and videos, managing jobs, and more. For a full list of commands and options, run `python facefusion.py --help`.

### Testing

The project includes a suite of tests in the `tests/` directory. The tests can be run using `pytest`:

```bash
pytest
```

## Development Conventions

The project follows standard Python development conventions. The code is formatted using `black` and linted with `flake8`. The project also uses `mypy` for static type checking.

The project has a modular architecture, with different functionalities separated into different modules. This makes it easy to extend the application with new features and processors.

All new features and bug fixes should be accompanied by corresponding tests to ensure the stability and reliability of the codebase.
