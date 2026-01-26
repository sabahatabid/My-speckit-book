"""Tests for the document ingestion pipeline."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.ingestion.parser import DocusaurusParser, Document, DocumentMetadata
from app.ingestion.chunker import SemanticChunker, TextChunk
from app.ingestion.pipeline import IngestionPipeline, IngestionResult


class TestDocusaurusParser:
    """Test the Docusaurus markdown parser."""

    def test_parse_frontmatter(self):
        """Test frontmatter parsing."""
        parser = DocusaurusParser("dummy_path")

        content = """---
title: Test Document
tags: [test, sample]
category: Tutorial
---

# Main Content
This is the content.
"""

        frontmatter = parser.parse_frontmatter(content)
        assert frontmatter["title"] == "Test Document"
        assert frontmatter["tags"] == ["test", "sample"]
        assert frontmatter["category"] == "Tutorial"

    def test_markdown_to_text(self):
        """Test markdown to text conversion."""
        parser = DocusaurusParser("dummy_path")

        markdown_content = """
# Heading 1

This is a paragraph with **bold** text.

- List item 1
- List item 2

```python
code block
```
"""

        text = parser.markdown_to_text(markdown_content)
        assert "Heading 1" in text
        assert "bold" in text
        assert "List item 1" in text
        assert "code block" not in text  # Code blocks should be removed


class TestSemanticChunker:
    """Test the semantic text chunker."""

    def test_count_tokens(self):
        """Test token counting."""
        chunker = SemanticChunker()
        text = "Hello world, this is a test."
        tokens = chunker.count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_split_text_basic(self):
        """Test basic text splitting."""
        chunker = SemanticChunker(chunk_size=50, overlap=10)

        # Create text longer than chunk size
        text = " ".join([f"word{i}" for i in range(100)])

        chunks = chunker.split_text(text)
        assert len(chunks) > 1

        # Check overlap
        if len(chunks) > 1:
            # Last few words of first chunk should appear in second chunk
            first_end = chunks[0].split()[-3:]  # Last 3 words
            second_start = chunks[1].split()[:3]  # First 3 words
            assert set(first_end) & set(second_start)  # Some overlap

    def test_chunk_document(self):
        """Test document chunking."""
        chunker = SemanticChunker(chunk_size=100, overlap=20)

        doc_content = "This is a test document. " * 50  # Repeat to make it long
        doc_path = "test.md"

        chunks = chunker.chunk_document(doc_content, doc_path)

        assert len(chunks) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(chunk.document_path == doc_path for chunk in chunks)
        assert all(chunk.chunk_id.startswith(f"{doc_path}#chunk-") for chunk in chunks)


@pytest.mark.asyncio
class TestIngestionPipeline:
    """Test the ingestion pipeline."""

    async def test_process_document(self):
        """Test processing a single document."""
        pipeline = IngestionPipeline("dummy_path")

        # Create mock document
        metadata = DocumentMetadata(
            title="Test Doc",
            path="test.md",
            category="Test"
        )
        document = Document(
            content="This is test content for chunking. It should be split appropriately.",
            metadata=metadata,
            raw_markdown="# Test\n\nThis is test content."
        )

        chunks = await pipeline.process_document(document)

        assert len(chunks) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)

    async def test_run_ingestion_no_documents(self):
        """Test ingestion with no documents found."""
        with patch.object(DocusaurusParser, 'parse_all', return_value=[]):
            pipeline = IngestionPipeline("nonexistent_path")
            result = await pipeline.run_ingestion()

            assert not result.success
            assert result.documents_processed == 0
            assert "No documents found" in result.errors[0]

    def test_validate_ingestion(self):
        """Test chunk validation."""
        pipeline = IngestionPipeline("dummy_path")

        # Create mock chunks
        chunks = [
            TextChunk(
                content="Short chunk",
                chunk_id="test-1",
                document_path="test.md",
                start_position=0,
                end_position=12,
                metadata={},
                token_count=3
            ),
            TextChunk(
                content="",  # Empty chunk
                chunk_id="test-2",
                document_path="test.md",
                start_position=12,
                end_position=12,
                metadata={},
                token_count=0
            )
        ]

        validation = pipeline.validate_ingestion(chunks)

        assert validation["total_chunks"] == 2
        assert validation["empty_chunks"] == 1
        assert "empty chunks" in str(validation["warnings"])


if __name__ == "__main__":
    pytest.main([__file__])