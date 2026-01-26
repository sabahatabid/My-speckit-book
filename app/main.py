"""FastAPI application for the RAG Chatbot backend."""

import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .ingestion.pipeline import IngestionPipeline, IngestionResult, TextChunk


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic models for API
class IngestionRequest(BaseModel):
    """Request model for document ingestion."""
    docs_path: str = None  # Optional override of configured path


class IngestionResponse(BaseModel):
    """Response model for ingestion results."""
    success: bool
    documents_processed: int
    chunks_created: int
    total_tokens: int
    errors: List[str]
    validation: Dict[str, Any] = None    
    database_status: str = "not_configured"  # New field

class ChunkResponse(BaseModel):
    """Response model for chunk data."""
    chunk_id: str
    content: str
    document_path: str
    metadata: Dict[str, Any]
    token_count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


# Global variables for background tasks
ingestion_results: Dict[str, IngestionResult] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting RAG Chatbot backend")
    yield
    logger.info("Shutting down RAG Chatbot backend")


# Create FastAPI app
app = FastAPI(
    title="RAG Chatbot Backend",
    description="Retrieval-Augmented Generation Chatbot for Docusaurus Documentation",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


@app.post("/ingest", response_model=IngestionResponse)
async def ingest_documents(request: IngestionRequest, background_tasks: BackgroundTasks):
    """Trigger document ingestion and chunking."""
    try:
        # Use configured path if not specified
        docs_path = request.docs_path or settings.docusaurus_docs_path

        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            docs_path=docs_path,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )

        # Run ingestion (this could be moved to background for large datasets)
        result = await pipeline.run_ingestion()

        # For now, store result globally (in production, use proper storage)
        ingestion_results["latest"] = result

        # Validate results
        if result.success and result.chunks_created > 0:
            # Create a mock chunk list for validation (in real implementation, chunks would be stored)
            mock_chunks = [
                TextChunk(
                    content=f"Sample chunk {i}",
                    chunk_id=f"sample-{i}",
                    document_path="sample.md",
                    start_position=i*100,
                    end_position=(i+1)*100,
                    metadata={"sample": True},
                    token_count=50
                ) for i in range(min(10, result.chunks_created))
            ]
            validation = pipeline.validate_ingestion(mock_chunks)
        else:
            validation = None

        return IngestionResponse(
            success=result.success,
            documents_processed=result.documents_processed,
            chunks_created=result.chunks_created,
            total_tokens=result.total_tokens,
            errors=result.errors,
            validation=validation,
            database_status="available" if settings.database_url and "sqlite" not in settings.database_url else "sqlite_fallback"
        )

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/ingest/status")
async def get_ingestion_status():
    """Get the status of the latest ingestion."""
    if "latest" not in ingestion_results:
        return {"status": "No ingestion completed yet"}

    result = ingestion_results["latest"]
    return {
        "status": "completed" if result.success else "failed",
        "documents_processed": result.documents_processed,
        "chunks_created": result.chunks_created,
        "total_tokens": result.total_tokens,
        "errors": result.errors
    }


@app.get("/chunks", response_model=List[ChunkResponse])
async def get_chunks(limit: int = 10, offset: int = 0):
    """Get sample chunks (for testing - in production, this would query the vector store)."""
    # This is a mock implementation - in real system, chunks would be retrieved from Qdrant
    mock_chunks = [
        ChunkResponse(
            chunk_id=f"mock-chunk-{i}",
            content=f"This is mock chunk content {i} with some sample text for testing purposes.",
            document_path=f"docs/sample-{i}.md",
            metadata={"category": "sample", "tags": ["test"]},
            token_count=25
        ) for i in range(limit)
    ]

    return mock_chunks[offset:offset + limit]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )