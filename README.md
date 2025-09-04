# TLDR - AI Meeting Summarization Tool

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready AI tool that processes meeting transcripts from Teams/Zoom and generates structured summaries with action items, decisions, and next steps.

## 🚀 Features

- **Multi-Platform Support**: Teams, Zoom, Google Meet integration
- **Real-Time Processing**: Fast transcript analysis and summarization
- **Smart Extraction**: Automatically identifies action items, decisions, and key topics
- **Multiple Output Formats**: Export summaries in various formats
- **Security First**: Enterprise-grade security and privacy compliance
- **Scalable Architecture**: Built for high-volume processing

## 📋 Quick Start

### Prerequisites

- Python 3.11+
- UV package manager (recommended) or pip
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tldr.git
cd tldr

# Install with UV (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Or install with pip
pip install -r requirements.txt
```

### Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Configure your environment variables:
   ```bash
   # API Keys
   OPENAI_API_KEY=your_openai_key
   ASSEMBLYAI_API_KEY=your_assemblyai_key
   
   # Database
   DATABASE_URL=postgresql://user:password@localhost/tldr
   
   # Security
   SECRET_KEY=your_secret_key
   ```

### Running the Application

```bash
# Development server
uvicorn src.main:app --reload --port 8000

# Production server
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

Visit `http://localhost:8000` to access the API documentation.

## 📖 API Documentation

### Core Endpoints

- `POST /api/v1/transcripts/upload` - Upload audio/text files
- `POST /api/v1/transcripts/process` - Process transcripts
- `GET /api/v1/summaries/{meeting_id}` - Retrieve summaries
- `POST /api/v1/summaries/export` - Export in various formats

### Example Usage

```python
import httpx

# Upload and process a meeting transcript
async with httpx.AsyncClient() as client:
    # Upload transcript
    response = await client.post(
        "http://localhost:8000/api/v1/transcripts/upload",
        json={
            "meeting_id": "meeting_123",
            "raw_text": "Meeting transcript content...",
            "participants": ["Alice", "Bob"],
            "duration_minutes": 60
        }
    )
    
    # Process transcript
    summary = await client.post(
        "http://localhost:8000/api/v1/transcripts/process",
        json={"meeting_id": "meeting_123"}
    )
```

## 🏗️ Architecture

### Project Structure

```
tldr/
├── src/
│   ├── transcription/    # Audio-to-text services
│   ├── summarization/    # AI summarization logic
│   ├── integrations/     # Teams/Zoom/Meet APIs
│   ├── api/             # FastAPI routes
│   ├── core/            # Configuration & utilities
│   └── models/          # Data models
├── tests/               # Test suite
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── docker/              # Container configurations
```

### Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: OpenAI GPT-4, AssemblyAI, LangChain
- **Database**: PostgreSQL
- **Testing**: Pytest with 80%+ coverage
- **Linting**: Ruff, Black, MyPy
- **Deployment**: Docker, Kubernetes

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
uv pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest --cov=src --cov-report=html

# Run linting
ruff check src/
black --check src/
mypy src/
```

## 📊 Testing

We maintain 80%+ test coverage:

```bash
# Run full test suite
pytest --cov=src --cov-report=term-missing

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 🔒 Security

Please report security vulnerabilities via our [Security Policy](SECURITY.md).

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com) for the excellent web framework
- [AssemblyAI](https://assemblyai.com) for accurate transcription services
- [OpenAI](https://openai.com) for powerful language models
- [LangChain](https://langchain.com) for AI orchestration patterns

---

**Built with ❤️ for better meeting productivity**