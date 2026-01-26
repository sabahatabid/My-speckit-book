# RAG Chatbot Backend

Retrieval-Augmented Generation Chatbot backend for Docusaurus technical documentation.

## Features

- **Document Ingestion**: Parse and process Docusaurus markdown files
- **Semantic Chunking**: Intelligent text splitting with overlap
- **FastAPI Backend**: RESTful API for document processing
- **Async Processing**: Concurrent document processing for performance

## Project Structure

```
chatbot/backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration management
│   └── ingestion/
│       ├── __init__.py
│       ├── parser.py    # Docusaurus markdown parser
│       ├── chunker.py   # Semantic text chunker
│       └── pipeline.py  # Ingestion orchestration
├── tests/
│   ├── __init__.py
│   └── test_ingestion.py # Unit tests
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template
```

## Setup

1. **Install Dependencies**
   ```bash
   cd chatbot/backend
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Run the Application**
   ```bash
   python -m app.main
   ```

   The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```http
GET /health
```

### Document Ingestion
```http
POST /ingest
Content-Type: application/json

{
  "docs_path": "../docs"  // Optional: override configured docs path
}
```

### Ingestion Status
```http
GET /ingest/status
```

### Get Chunks (Testing)
```http
GET /chunks?limit=10&offset=0
```

## Testing

### Run Unit Tests
```bash
cd chatbot/backend
python -m pytest tests/ -v
```

### Test the Ingestion Pipeline
```bash
# Start the server
python -m app.main

# In another terminal, test ingestion
curl -X POST "http://localhost:8000/ingest" \
     -H "Content-Type: application/json" \
     -d '{"docs_path": "../../../docs"}'
```

### Validate API Health
```bash
curl http://localhost:8000/health
```

## Configuration

Environment variables (see `.env.example`):

- `OPENAI_API_KEY`: OpenAI API key (for future embedding generation)
- `QDRANT_URL`: Qdrant Cloud URL (for future vector storage)
- `QDRANT_API_KEY`: Qdrant API key
- `DATABASE_URL`: Neon Postgres connection string
- `DOCUSAURUS_DOCS_PATH`: Path to Docusaurus docs directory
- `CHUNK_SIZE`: Text chunk size in characters (default: 1000)
- `CHUNK_OVERLAP`: Chunk overlap in characters (default: 200)

## Development

### Code Quality
- Uses type hints throughout
- Comprehensive error handling
- Async/await for performance
- Modular architecture for maintainability

### Testing Strategy
- Unit tests for all components
- Mock external dependencies
- Async test support
- Validation of edge cases

## Next Steps

This implementation covers Task 1: Markdown ingestion and chunking pipeline. Future tasks will add:

- Vector embeddings with OpenAI
- Qdrant vector storage
- Query processing and retrieval
- ChatKit integration
- Docusaurus UI components