"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model for generation")
    openai_embedding_model: str = Field(
        default="text-embedding-ada-002", description="OpenAI embedding model"
    )

    # Pinecone Configuration
    pinecone_api_key: str = Field(..., description="Pinecone API key")
    pinecone_index_name: str = Field(
        default="requirements-analysis", description="Pinecone index name"
    )
    pinecone_environment: str = Field(default="us-east-1", description="Pinecone environment")

    # Application Settings
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )
    app_debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")

    # Document Processing
    chunk_size: int = Field(default=512, description="Chunk size in tokens")
    chunk_overlap: int = Field(default=50, description="Chunk overlap in tokens")
    max_upload_size_mb: int = Field(default=50, description="Maximum upload size in MB")

    # RAG Configuration
    rag_top_k: int = Field(default=5, description="Number of documents to retrieve")
    rag_score_threshold: float = Field(
        default=0.7, description="Minimum similarity score threshold"
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
