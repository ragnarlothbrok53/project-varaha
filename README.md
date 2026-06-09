# Project Varaha: AI-Powered Document Processing and Analysis Platform

## Project Overview

Project Varaha is a comprehensive platform designed for advanced document processing and analysis, leveraging AI and machine learning techniques. It provides capabilities for extracting, classifying, summarizing, and rewriting information from various document types, including PDFs and DOCX files. The platform is built with a focus on scalability, performance, and robust API-driven interactions.

## Key Features

*   **Multi-Document Support:** Processes PDF and DOCX files for information extraction and analysis.
*   **AI-Powered Task Automation:** Integrates tasks such as chat, classification, extraction, rewriting, and summarization using various AI models.
*   **Scalable Backend:** Built with FastAPI, ensuring high performance and efficient handling of concurrent requests.
*   **Asynchronous Processing:** Utilizes `asyncio` and background workers for non-blocking operations and efficient task management.
*   **Rate Limiting and Security:** Implements rate limiting with `slowapi` and authentication with `pyjwt` for robust API security.
*   **Frontend Interface:** Features a modern frontend built with Astro, providing a user-friendly dashboard for project management and interaction.
*   **Local LLM Integration:** Supports `llama-cpp-python` for local execution of large language models, enabling privacy-preserving and cost-effective AI operations.

## Technical Stack

*   **Backend Framework:** FastAPI
*   **Asynchronous Programming:** `asyncio`
*   **Document Processing:** `pypdf`, `python-docx`
*   **Machine Learning/AI:** `llama-cpp-python`, `scikit-learn`, `sentence-transformers`
*   **Security:** `bcrypt`, `pyjwt`, `slowapi`
*   **Frontend Framework:** Astro
*   **Database:** SQLite (indicated by `varaha_metrics.db`)
*   **Language:** Python 3.13+

## Getting Started

To set up and run Project Varaha, follow these steps:

### Prerequisites

*   Python 3.13+
*   Node.js and npm/yarn (for frontend development)

### Installation and Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ragnarlothbrok53/project-varaha.git
    cd project-varaha
    ```
2.  **Backend Setup:**
    ```bash
    # Install Python dependencies
    pip install -e .
    # Run the application
    python -m uvicorn app.main:app --reload
    ```
3.  **Frontend Setup:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## Project Structure

*   **`app/`**: Contains the backend FastAPI application, including API routes, core logic, data management, services, and AI tasks.
*   **`frontend/`**: Houses the Astro-based frontend application, providing the user interface.
*   **`tests/`**: Includes benchmarking and evaluation scripts for the AI models.
*   **`PRODUCTION_READINESS_REPORT.md`**: Documentation related to production deployment considerations.

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` (if available) for guidelines.

## License

This project is licensed under the MIT license - see the `LICENSE` file for details.
