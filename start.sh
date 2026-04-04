#!/bin/bash

# Configuration
PORT=${1:-8000}

# 🔍 Pre-flight check: Model exists?
if [ ! -d "models" ] || [ -z "$(ls models/*.gguf 2>/dev/null)" ]; then
    echo "❌ Error: No .gguf models found in 'models/' directory."
    echo "💡 Please place a model file (e.g. qwen.gguf) in the models/ folder and try again."
    exit 1
fi

echo "🚀 Starting Varaha LLM Server on port $PORT..."

# Start in background using uv run
# We disable uvicorn's default logging to favor our structured production logger
uv run uvicorn app.main:app --port $PORT --no-access-log --log-level critical &
SERVER_PID=$!

# Function to clean up background process on exit
cleanup() {
    echo "Stopping server (PID: $SERVER_PID)..."
    kill $SERVER_PID
    exit
}
trap cleanup SIGINT SIGTERM

echo "⏳ Waiting for server to initialize engine and be healthy..."
MAX_RETRIES=30
RETRY_COUNT=0
while ! curl -s "http://localhost:$PORT/docs" > /dev/null; do
    sleep 1
    let RETRY_COUNT=RETRY_COUNT+1
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Server failed to start in time."
        kill $SERVER_PID
        exit 1
    fi
done

echo "✅ Server is up! Running automated semantic evaluation test..."

# Test with our golden dataset
uv run python -m tests.evaluator "http://localhost:$PORT"

echo "⚡ Running Concurrency Benchmark (Latency & Throughput)..."
uv run python -m tests.bencher "http://localhost:$PORT" 5 20

echo -e "\n\n🎉 Startup verification complete. Server logs will appear below. Use Ctrl+C to stop."

# Bring background process to foreground
wait $SERVER_PID
