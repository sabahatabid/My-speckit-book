"""Ingestion pipeline for processing documents and creating chunks."""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import logging

from .parser import DocusaurusParser, Document
from .chunker import SemanticChunker, TextChunk


@dataclass
class IngestionResult:
    """Result of document ingestion process."""
    documents_processed: int
    chunks_created: int
    total_tokens: int
    errors: List[str]
    success: bool


@dataclass
class IngestionProgress:
    """Progress tracking for ingestion process."""
    current_document: int
    total_documents: int
    current_chunk: int
    total_chunks: int
    status: str


class IngestionPipeline:
    """Pipeline for ingesting and chunking documents."""

    def __init__(self, docs_path: str, chunk_size: int = 1000, overlap: int = 200):
        """Initialize the ingestion pipeline."""
        self.docs_path = docs_path
        self.chunk_size = chunk_size
        self.overlap = overlap

        self.parser = DocusaurusParser(docs_path)
        self.chunker = SemanticChunker(chunk_size, overlap)

        self.logger = logging.getLogger(__name__)

    async def process_document(self, document: Document) -> List[TextChunk]:
        """Process a single document into chunks."""
        try:
            # Chunk the document content
            chunks = self.chunker.chunk_document(
                document_content=document.content,
                document_path=document.metadata.path,
                metadata={
                    'title': document.metadata.title,
                    'category': document.metadata.category,
                    'tags': document.metadata.tags,
                    'author': document.metadata.author,
                }
            )

            self.logger.info(f"Processed document '{document.metadata.title}' into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            self.logger.error(f"Error processing document '{document.metadata.path}': {e}")
            return []

    async def process_documents_batch(self, documents: List[Document], batch_size: int = 10) -> List[TextChunk]:
        """Process documents in batches for better performance."""
        all_chunks = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1} of {(len(documents) + batch_size - 1)//batch_size}")

            # Process batch concurrently
            tasks = [self.process_document(doc) for doc in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch processing error: {result}")
                else:
                    all_chunks.extend(result)

        return all_chunks

    async def run_ingestion(self, progress_callback: Optional[callable] = None) -> IngestionResult:
        """Run the complete ingestion pipeline."""
        errors = []

        try:
            # Discover and parse documents
            self.logger.info("Starting document discovery and parsing...")
            documents = self.parser.parse_all()

            if not documents:
                return IngestionResult(
                    documents_processed=0,
                    chunks_created=0,
                    total_tokens=0,
                    errors=["No documents found to process"],
                    success=False
                )

            self.logger.info(f"Found {len(documents)} documents to process")

            # Update progress
            if progress_callback:
                progress_callback(IngestionProgress(
                    current_document=0,
                    total_documents=len(documents),
                    current_chunk=0,
                    total_chunks=0,
                    status="Processing documents..."
                ))

            # Process documents into chunks
            chunks = await self.process_documents_batch(documents)

            # Calculate total tokens
            total_tokens = sum(chunk.token_count for chunk in chunks)

            self.logger.info(f"Ingestion complete: {len(documents)} documents, {len(chunks)} chunks, {total_tokens} tokens")

            return IngestionResult(
                documents_processed=len(documents),
                chunks_created=len(chunks),
                total_tokens=total_tokens,
                errors=errors,
                success=True
            )

        except Exception as e:
            error_msg = f"Ingestion pipeline failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)

            return IngestionResult(
                documents_processed=0,
                chunks_created=0,
                total_tokens=0,
                errors=errors,
                success=False
            )

    def validate_ingestion(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Validate the quality of ingested chunks."""
        validation_results = {
            'total_chunks': len(chunks),
            'empty_chunks': 0,
            'oversized_chunks': 0,
            'average_chunk_size': 0,
            'average_tokens': 0,
            'chunk_size_distribution': {},
            'warnings': []
        }

        if not chunks:
            validation_results['warnings'].append("No chunks to validate")
            return validation_results

        total_chars = 0
        total_tokens = 0

        for chunk in chunks:
            # Check for empty chunks
            if not chunk.content.strip():
                validation_results['empty_chunks'] += 1
                continue

            # Check chunk size
            chunk_size = len(chunk.content)
            total_chars += chunk_size
            total_tokens += chunk.token_count

            if chunk_size > self.chunk_size * 1.5:  # Allow 50% tolerance
                validation_results['oversized_chunks'] += 1

            # Track size distribution
            size_bucket = (chunk_size // 100) * 100
            validation_results['chunk_size_distribution'][size_bucket] = \
                validation_results['chunk_size_distribution'].get(size_bucket, 0) + 1

        if chunks:
            validation_results['average_chunk_size'] = total_chars / len(chunks)
            validation_results['average_tokens'] = total_tokens / len(chunks)

        # Generate warnings
        if validation_results['empty_chunks'] > 0:
            validation_results['warnings'].append(f"Found {validation_results['empty_chunks']} empty chunks")

        if validation_results['oversized_chunks'] > 0:
            validation_results['warnings'].append(f"Found {validation_results['oversized_chunks']} oversized chunks")

        return validation_results