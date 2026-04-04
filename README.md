# Project Varaha: High-Performance LLM Proxy

Varaha is a batching proxy for local Large Language Model (LLM) inference, optimized specifically for Apple Silicon (Mac M1/M2/M3) using Metal acceleration.

## Features

- **Metal Acceleration**: Automatically utilizes Apple Silicon GPUs via `llama-cpp-python`.
- **Dynamic Batching**: Gathers incoming requests into batches for maximum throughput.
- **Task-Based API**: Built-in support for summarization, classification, extraction, and rewriting.
- **In-Memory Caching**: Avoids redundant processing for repeated prompts.
- **Rate Limiting**: Per-API-key usage policing.
- **FastAPI / Uvicorn**: High-performance asynchronous web server.

## Installation

Ensure you have `uv` installed, then set up your environment with Metal support:

```bash
CMAKE_ARGS="-DGGML_METAL=on" uv pip install llama-cpp-python
uv pip install -r requirements.txt
```

## Structure

- `app/main.py`: Entry point and lifespan management.
- `app/api.py`: Route handlers and execution logic.
- `app/engine.py`: LLM backend (llama-cpp-python).
- `app/worker.py`: Background batching worker and job queue.
- `app/config.py`: Configuration constants.
- `models/`: Place your `.gguf` model files here.

## Usage

Start the server and run initial tests:

```bash
./start.sh
```

The server runs on port `8000` by default. You can access the auto-generated documentation at `http://localhost:8000/docs`.

## License

MIT
