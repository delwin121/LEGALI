# Vidhi-Sahayak

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Vidhi-Sahayak is an offline, Retrieval-Augmented Generation (RAG) based
legal assistant designed to explain India's 2023 criminal law framework
(BNS, BNSS, BSA) using authoritative statutory text.

## Features

- **Recursive RAG (Parent–Child retrieval)**: Efficiently retrieves relevant context from legal documents.
- **Offline local LLM**: Designed to work with Ollama for privacy and offline capability.
- **Citation-backed responses**: Provides sources for the answers.
- **Dockerized**: Easy setup and reproducibility using Docker.

## Project Structure

```
.
├── backend/               # Backend application code
│   ├── app/               # Application logic (API, Streamlit, RAG pipeline)
│   ├── data/              # Data storage (ChromaDB, cleaned text)
│   ├── scripts/           # Utility scripts
│   ├── Dockerfile         # Docker configuration for backend
│   └── requirements.txt   # Python dependencies
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # Project documentation
```

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- [Ollama](https://ollama.com/) (if running local LLM)

### Installation & Running (Quick Start)

The easiest way to run Vidhi-Sahayak is using the provided startup script, which launches both the backend API and the frontend.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/vidhi-sahayak.git
    cd vidhi-sahayak
    ```

2.  **Run the startup script:**
    ```bash
    ./startup.sh
    ```

    This will start:
    - Backend API at `http://localhost:8000`
    - Frontend Application at `http://localhost:8080/pages/index.html`

    Open `http://localhost:8080/pages/index.html` in your browser to start using the application.

### Running with Docker

1.  **Build and run the container:**
    ```bash
    docker compose up --build
    ```

### Local Development

If you prefer to run it locally without Docker:

1.  **Navigate to the backend directory:**

    ```bash
    cd backend
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**

    (Adjust the command based on your entry point, e.g., for Streamlit)
    ```bash
    streamlit run app/streamlit_app.py
    ```
    OR for API
    ```bash
    uvicorn app.api:app --reload
    ```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
