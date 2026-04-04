#!/bin/bash

# Configuration
PORT=${1:-8000}

echo "🚀 Starting Varaha LLM Server on port $PORT..."

# Start in background using uv run
uv run uvicorn app.main:app --port $PORT --log-level info &
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

echo "✅ Server is up! Running initial readiness test..."

# Test Summarization task
curl -X POST "http://localhost:$PORT/v1/execute" \
     -H "Content-Type: application/json" \
     -H "Authorization: dev-key-123" \
     -d '{
       "task": "summarize",
       "input": {
         "text": "Antigravity has refactored the project into a modular structure. It now uses llama-cpp-python with Metal acceleration on Mac, replacing the old mock batch implementation."
       }
     }'

echo -e "\n\n🎉 Readiness test complete. Use Ctrl+C to stop the server and see logs."

# Bring background process to foreground
wait $SERVER_PID
