"""Document parser for Docusaurus markdown files."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml
import markdown
from bs4 import BeautifulSoup


@dataclass
class DocumentMetadata:
    """Metadata extracted from a document."""
    title: str
    path: str
    category: Optional[str] = None
    tags: List[str] = None
    last_modified: Optional[str] = None
    author: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class Document:
    """Represents a parsed document."""
    content: str
    metadata: DocumentMetadata
    raw_markdown: str


class DocusaurusParser:
    """Parser for Docusaurus markdown documentation."""

    def __init__(self, docs_path: str):
        """Initialize parser with docs directory path."""
        self.docs_path = Path(docs_path)
        self.frontmatter_pattern = re.compile(
            r'^---\s*\n(.*?)\n---\s*\n',
            re.MULTILINE | re.DOTALL
        )

    def parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown content."""
        match = self.frontmatter_pattern.search(content)
        if not match:
            return {}

        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    def extract_title_from_content(self, content: str) -> str:
        """Extract title from markdown content if not in frontmatter."""
        # Look for the first heading
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('# '):
                return line.strip()[2:].strip()
        return "Untitled Document"

    def markdown_to_text(self, markdown_content: str) -> str:
        """Convert markdown to plain text."""
        # Remove frontmatter first
        content = self.frontmatter_pattern.sub('', markdown_content)

        # Convert to HTML then extract text
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, 'html.parser')

        # Remove code blocks and pre tags
        for tag in soup.find_all(['code', 'pre']):
            tag.decompose()

        # Extract text
        text = soup.get_text()

        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def parse_file(self, file_path: Path) -> Optional[Document]:
        """Parse a single markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            # Parse frontmatter
            frontmatter = self.parse_frontmatter(raw_content)

            # Extract metadata
            title = frontmatter.get('title') or self.extract_title_from_content(raw_content)
            category = frontmatter.get('sidebar_label') or frontmatter.get('category')
            tags = frontmatter.get('tags', [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',')]
            author = frontmatter.get('author')

            # Get relative path for metadata
            relative_path = file_path.relative_to(self.docs_path)

            metadata = DocumentMetadata(
                title=title,
                path=str(relative_path),
                category=category,
                tags=tags,
                author=author
            )

            # Convert to plain text
            content = self.markdown_to_text(raw_content)

            return Document(
                content=content,
                metadata=metadata,
                raw_markdown=raw_content
            )

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def discover_files(self) -> List[Path]:
        """Discover all markdown files in the docs directory."""
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Docs path does not exist: {self.docs_path}")

        markdown_files = []
        for pattern in ['**/*.md', '**/*.mdx']:
            markdown_files.extend(self.docs_path.glob(pattern))

        return sorted(markdown_files)

    def parse_all(self) -> List[Document]:
        """Parse all markdown files in the docs directory."""
        files = self.discover_files()
        documents = []

        for file_path in files:
            doc = self.parse_file(file_path)
            if doc:
                documents.append(doc)

        return documents