# Varaha: High-Performance Modular LLM Proxy

Varaha is a production-ready LLM proxy designed for local batching and modular tasks, specifically optimized for **Apple Silicon**. It allows you to run specialized LLM instructions (Summarization, Extraction, Classification, Rewriting) with high throughput and integrated quality monitoring.

## 🚀 Key Features

*   **Apple Silicon Native**: Real Metal-accelerated inference via `llama-cpp-python`.
*   **Modular Tasks**: Extensible task registry found in `app/tasks/`. Easily add new model instructions by creating a single Python class.
*   **Dynamic Batching**: In-memory queuing and background batch processing for maximum throughput.
*   **Prompt Compression**: Integrated "plug-and-play" compression to minimize token overhead and latency.
*   **Performance Monitoring**: Persistent SQLite storage for TTFT (Time To First Token), token counts, and TPS (Tokens Per Second).
*   **Automated Evaluation**: Built-in semantic similarity pipeline that validates model outputs against a "golden" dataset on every startup.
*   **Production Security**: Rate limiting, input validation, JWT authentication, and password recovery.

## 🛠️ Getting Started

### Prerequisites
*   Hardware: M1/M2/M3 Mac (recommended) or any system with `llama.cpp` support.
*   Tools: [uv](https://github.com/astral-sh/uv) (high-speed Python dependency manager).

### Installation
1. Clone the repository and place your `.gguf` model files in `models/` directory.
2. Create a `.env` file for production configuration:
```bash
# Security
JWT_SECRET=your-super-secret-jwt-key-here
DEBUG=false

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Email (for password recovery)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=noreply@yourdomain.com

# Database (for future PostgreSQL migration)
DATABASE_URL=sqlite:///./varaha_metrics.db
```
3. Run the automated setup and startup script:
```bash
chmod +x start.sh
./start.sh
```

## � Available Tasks & API Examples

### 1. Chat Completion
**OpenAI-Compatible Endpoint**
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

### 2. Text Summarization
**Task Type**: `summarize`
```bash
curl -X POST "http://localhost:8000/v1/execute" \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "summarize",
    "input": {
      "text": "The quick brown fox jumps over the lazy dog. This pangram sentence contains all letters of the English alphabet and is commonly used for testing typefaces and keyboard functionality. It has been in use since the late 19th century and remains one of the most recognized sentences in the English language."
    },
    "config": {
      "max_tokens": 100,
      "temperature": 0.3
    }
  }'
```

### 3. Information Extraction
**Task Type**: `extract`
```bash
curl -X POST "http://localhost:8000/v1/execute" \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "extract",
    "input": {
      "text": "Invoice #INV-2024-001 from Acme Corp dated March 15, 2024 for $2,450.00. Payment due within 30 days. Contact: john@acmecorp.com, Phone: (555) 123-4567.",
      "schema": {
        "invoice_number": "string",
        "company": "string", 
        "amount": "number",
        "due_date": "string",
        "contact_email": "string",
        "contact_phone": "string"
      }
    }
  }'
```

### 4. Text Classification
**Task Type**: `classify`
```bash
curl -X POST "http://localhost:8000/v1/execute" \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "classify",
    "input": {
      "text": "I love this product! It works exactly as described and the quality is amazing. Highly recommend!",
      "labels": ["positive", "negative", "neutral"]
    }
  }'
```

### 5. Text Rewriting
**Task Type**: `rewrite`
```bash
curl -X POST "http://localhost:8000/v1/execute" \
  -H "Authorization: Bearer admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "rewrite",
    "input": {
      "text": "The meeting was very good and we discussed many important topics.",
      "instruction": "Make this more professional and specific"
    }
  }'
```

## 🔧 Configuration Options

### Task Configuration
All tasks support optional configuration parameters:

```json
{
  "config": {
    "temperature": 0.7,        // 0.0 to 1.0 (default: 0.7)
    "max_tokens": 256,         // Maximum tokens to generate
    "compress": true,           // Enable prompt compression (default: true)
    "system_prompt": "Custom instructions" // Override default system prompt
  }
}
```

### Model Selection
- `qwen`: Qwen 1.5B Turbo (Fast) - **Default**
- `tinyllama`: TinyLlama 1.1B Eco (Resource-efficient)

## 📊 API Documentation

### Authentication
All API endpoints require authentication using an API key:

```bash
# Get your API key from the dashboard or use default
curl -H "Authorization: Bearer your-api-key-here"
```

### Rate Limiting
- **Default**: 100 requests per minute per IP
- **Configurable**: Set via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW` environment variables

### Response Format
All responses follow consistent format:

```json
{
  "success": true,
  "result": "Generated text here...",
  "task_id": "uuid-here",
  "tokens_used": 45,
  "execution_time": 1.23
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
*   `app/api/schemas.py`: Input validation models.
*   `app/utils/config.py`: Environment configuration management.

## 🔒 Security Features

### Authentication
- JWT-based user authentication
- API key validation for all requests
- Secure password hashing with bcrypt

### Input Validation
- Pydantic models for all API inputs
- SQL injection prevention
- XSS protection

### Rate Limiting
- Configurable per-IP rate limits
- Protection against DoS attacks
- Automatic request throttling

### Password Recovery
- Email-based password reset
- Secure token generation
- Configurable SMTP settings

## 🚀 Production Deployment

### Environment Variables
```bash
# Application
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security
JWT_SECRET=your-production-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=noreply@yourdomain.com

# Database (future PostgreSQL support)
DATABASE_URL=postgresql://user:pass@localhost/varaha
```

### Docker Deployment (Coming Soon)
```dockerfile
# Dockerfile will be added in next iteration
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🧪 Testing

### Automated Evaluation
The system runs automated semantic similarity tests on startup:
```bash
# Run evaluation manually
uv run python -m tests.evaluator "http://localhost:8000"
```

### Performance Benchmarking
Test concurrency and throughput:
```bash
# Run 5 concurrent requests, 20 total
uv run python -m tests.bencher "http://localhost:8000" 5 20
```

## 🤝 Contributing

### Adding New Tasks
1. Create a new file in `app/tasks/`
2. Inherit from the base task class
3. Implement the required methods
4. Register the task in the task registry

Example:
```python
from .base import BaseTask

class CustomTask(BaseTask):
    def __init__(self):
        super().__init__("custom", "Custom task description")
    
    def build_prompt(self, input_data):
        return f"Custom prompt: {input_data['text']}"
    
    def parse_response(self, response):
        return {"result": response.strip()}
```

## ⚖️ License
MIT
