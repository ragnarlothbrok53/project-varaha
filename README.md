# Varaha: High-Performance Modular LLM Proxy

Varaha is a production-ready LLM proxy designed for local batching and modular tasks, specifically optimized for **Apple Silicon**. It allows you to run specialized LLM instructions (Summarization, Extraction, Classification, Rewriting) with high throughput and integrated quality monitoring.

## 🚀 Key Features

*   **Apple Silicon Native**: Real Metal-accelerated inference via `llama-cpp-python`.
*   **Modular Tasks**: Extensible task registry found in `app/tasks/`. Easily add new model instructions by creating a single Python class.
*   **Dynamic Batching**: In-memory queuing and background batch processing for maximum throughput.
*   **Prompt Compression**: Integrated "plug-and-play" compression to minimize token overhead and latency.
*   **Performance Monitoring**: Persistent SQLite storage for TTFT (Time To First Token), token counts, and TPS (Tokens Per Second).
*   **Automated Evaluation**: Built-in semantic similarity pipeline that validates model outputs against a "golden" dataset on every startup.

## 🛠️ Getting Started

### Prerequisites
*   Hardware: M1/M2/M3 Mac (recommended) or any system with `llama.cpp` support.
*   Tools: [uv](https://github.com/astral-sh/uv) (high-speed Python dependency manager).

### Installation
1. Clone the repository and place your `.gguf` model files in the `models/` directory.
2. Run the automated setup and startup script:
```bash
chmod +x start.sh
./start.sh
```

## 📊 API Documentation

### Execute a Task
`POST /v1/execute`
```json
{
  "task": "extract",
  "input": {
    "text": "Invoice #42 from Bob for $500",
    "schema": {"invoice": "number", "amount": "number"}
  },
  "config": {
    "compress": true
  }
}
```

### Check Performance Metrics
*   `GET /v1/requests`: List all processed job IDs.
*   `GET /v1/requests/{id}/metrics`: Retrieve detailed latency and token benchmarks from the SQLite store.

## 🏗️ Project Structure
*   `app/tasks/`: Define custom LLM logic and templates.
*   `app/engine.py`: Hardware-accelerated inference management.
*   `app/worker.py`: Async batching and background job execution.
*   `app/evaluator.py`: Semantic scoring and regression testing.
*   `app/database.py`: Persistent performance logging.

## ⚖️ License
MIT
