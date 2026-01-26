"""Configuration management for the RAG Chatbot backend."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # OpenAI Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.openai_api_key:
            print("WARNING: OPENAI_API_KEY not set in environment variables")

        # Qdrant Configuration
        self.qdrant_url = os.getenv("QDRANT_URL", "")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", "")

        # Database Configuration
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

        # Application Configuration
        self.debug = os.getenv("DEBUG", "0").lower() in ("true", "1", "yes")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Content Configuration
        self.docusaurus_docs_path = os.getenv("DOCUSAURUS_DOCS_PATH", "../docs")

        # Chunking Configuration
        try:
            self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        except ValueError:
            self.chunk_size = 1000

        try:
            self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        except ValueError:
            self.chunk_overlap = 200


# Global settings instance
settings = Settings()