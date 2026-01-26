"""Text chunking utilities for document processing."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    content: str
    chunk_id: str
    document_path: str
    start_position: int
    end_position: int
    metadata: Dict[str, Any]
    token_count: int


class SemanticChunker:
    """Intelligent text chunker with semantic awareness."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """Initialize chunker with size and overlap parameters."""
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 encoding

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))

    def find_sentence_boundaries(self, text: str) -> List[int]:
        """Find positions of sentence boundaries."""
        # Simple sentence boundary detection
        pattern = r'(?<=[.!?])\s+'
        boundaries = []
        for match in re.finditer(pattern, text):
            boundaries.append(match.end())
        return boundaries

    def find_paragraph_boundaries(self, text: str) -> List[int]:
        """Find positions of paragraph boundaries."""
        boundaries = []
        for match in re.finditer(r'\n\s*\n', text):
            boundaries.append(match.end())
        return boundaries

    def find_heading_boundaries(self, text: str) -> List[int]:
        """Find positions of markdown heading boundaries."""
        boundaries = []
        for match in re.finditer(r'^#{1,6}\s+.*$', text, re.MULTILINE):
            boundaries.append(match.end())
        return boundaries

    def get_optimal_split_points(self, text: str, max_length: int) -> List[int]:
        """Find optimal split points within text segment."""
        boundaries = []

        # Add different types of boundaries with priorities
        boundaries.extend([(pos, 3) for pos in self.find_sentence_boundaries(text)])
        boundaries.extend([(pos, 2) for pos in self.find_paragraph_boundaries(text)])
        boundaries.extend([(pos, 1) for pos in self.find_heading_boundaries(text)])

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Filter boundaries within our segment
        valid_boundaries = [pos for pos, priority in boundaries if pos <= max_length]

        if valid_boundaries:
            # Return the best boundary (highest priority, closest to max_length)
            best_boundary = max(valid_boundaries, key=lambda x: (boundaries[[p for p, _ in boundaries].index(x)][1], x))
            return [best_boundary]

        return []

    def split_text(self, text: str) -> List[str]:
        """Split text into chunks with semantic awareness."""
        if not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position for this chunk
            end = min(start + self.chunk_size, text_length)

            # If we're not at the end, try to find a better split point
            if end < text_length:
                remaining_text = text[start:end + 100]  # Look ahead a bit
                split_points = self.get_optimal_split_points(remaining_text, self.chunk_size)

                if split_points:
                    end = start + split_points[0]
                else:
                    # Fallback: split at word boundary
                    chunk_text = text[start:end]
                    last_space = chunk_text.rfind(' ')
                    if last_space > self.chunk_size // 2:  # Don't split too early
                        end = start + last_space

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Calculate next start position with overlap
            next_start = end - self.overlap
            if next_start <= start:
                next_start = end  # Avoid infinite loop

            start = next_start

        return chunks

    def chunk_document(self, document_content: str, document_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """Chunk a document into TextChunk objects."""
        if metadata is None:
            metadata = {}

        # Split text into chunks
        text_chunks = self.split_text(document_content)

        chunks = []
        current_position = 0

        for i, chunk_content in enumerate(text_chunks):
            # Calculate positions
            start_pos = current_position
            end_pos = start_pos + len(chunk_content)

            # Create chunk metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(text_chunks),
            })

            # Count tokens
            token_count = self.count_tokens(chunk_content)

            # Create chunk object
            chunk = TextChunk(
                content=chunk_content,
                chunk_id=f"{document_path}#chunk-{i}",
                document_path=document_path,
                start_position=start_pos,
                end_position=end_pos,
                metadata=chunk_metadata,
                token_count=token_count
            )

            chunks.append(chunk)
            current_position = end_pos - self.overlap  # Account for overlap

        return chunks