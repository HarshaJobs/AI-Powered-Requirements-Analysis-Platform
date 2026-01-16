# AI-Powered Requirements Analysis Platform

GenAI platform for automated requirements extraction, RAG-enhanced BRD querying, user story generation, and conflict detection.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **AI/ML**: LangChain, OpenAI GPT-4o, text-embedding-ada-002
- **Vector DB**: Pinecone (Serverless)
- **Deployment**: Docker, GCP Cloud Run

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Pinecone API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd "AI-Powered Requirements Analysis Platform"

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Configure environment
copy .env.example .env
# Edit .env with your API keys
```

### Run Locally

```bash
# Start the development server
python -m uvicorn src.main:app --reload --port 8080

# Access the API docs
# http://localhost:8080/docs
```

### Run with Docker

```bash
# Build the image
docker build -t req-analysis-api .

# Run the container
docker run -p 8080:8080 --env-file .env req-analysis-api
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/documents/upload` | POST | Upload document |
| `/api/v1/documents/index` | POST | Index to Pinecone |
| `/api/v1/extract/requirements` | POST | Extract requirements |
| `/api/v1/stories/generate` | POST | Generate user stories |
| `/api/v1/conflicts/analyze` | POST | Detect conflicts |
| `/api/v1/rag/query` | POST | Query knowledge base |

## Project Structure

```
src/
├── main.py                 # FastAPI entry point
├── config.py               # Configuration
├── api/routes/             # API endpoints
├── document_processing/    # PDF/text loaders, chunking
├── embeddings/             # OpenAI embedding generation
├── vectorstore/            # Pinecone operations
├── rag/                    # RAG pipeline
├── extractors/             # Requirement/story/conflict extraction
├── prompts/                # LLM prompt templates
└── schemas/                # Pydantic models
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | Model for generation | `gpt-4o` |
| `PINECONE_API_KEY` | Pinecone API key | Required |
| `CHUNK_SIZE` | Token chunk size | `512` |
| `CHUNK_OVERLAP` | Token overlap | `50` |
| `RAG_TOP_K` | Results to retrieve | `5` |

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=html
```

## Deployment to GCP Cloud Run

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create Artifact Registry repository
gcloud artifacts repositories create requirements-analysis \
    --repository-format=docker \
    --location=us-central1

# Store secrets
echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-pinecone-key" | gcloud secrets create pinecone-api-key --data-file=-

# Deploy (triggers cloudbuild.yaml)
gcloud builds submit
```

## License

MIT
