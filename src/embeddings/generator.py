"""OpenAI embedding generation for documents."""

from typing import Optional

import structlog
from langchain_openai import OpenAIEmbeddings

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings using OpenAI's embedding models.
    
    Uses OpenAI's text-embedding-ada-002 or other models as configured.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the embedding generator."""
        self.settings = settings or get_settings()
        self.embeddings = OpenAIEmbeddings(
            model=self.settings.openai_embedding_model,
            openai_api_key=self.settings.openai_api_key,
        )
        
        logger.info(
            "EmbeddingGenerator initialized",
            model=self.settings.openai_embedding_model,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of documents.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (list of floats)
        """
        try:
            logger.debug(
                "Generating embeddings",
                num_documents=len(texts),
            )
            
            embeddings = self.embeddings.embed_documents(texts)
            
            logger.info(
                "Embeddings generated",
                num_embeddings=len(embeddings),
                embedding_dim=len(embeddings[0]) if embeddings else 0,
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(
                "Error generating embeddings",
                error=str(e),
                num_documents=len(texts),
            )
            raise ValueError(f"Failed to generate embeddings: {str(e)}") from e

    def embed_query(self, text: str) -> list[float]:
        """
        Generate embedding for a single query text.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector (list of floats)
        """
        try:
            embedding = self.embeddings.embed_query(text)
            
            logger.debug(
                "Query embedding generated",
                text_length=len(text),
                embedding_dim=len(embedding),
            )
            
            return embedding
            
        except Exception as e:
            logger.error(
                "Error generating query embedding",
                error=str(e),
                text_length=len(text),
            )
            raise ValueError(f"Failed to generate query embedding: {str(e)}") from e
