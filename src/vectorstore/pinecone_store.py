"""Pinecone vector store integration."""

from typing import Optional, Any
from uuid import uuid4

import structlog
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.embeddings.generator import EmbeddingGenerator

logger = structlog.get_logger(__name__)


class PineconeVectorStoreManager:
    """
    Manages Pinecone vector store operations:
    - Index creation/connection
    - Document upsertion
    - Similarity search
    - Metadata filtering
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the Pinecone vector store manager."""
        self.settings = settings or get_settings()
        self.pinecone = Pinecone(api_key=self.settings.pinecone_api_key)
        self.embedding_generator = EmbeddingGenerator(settings=self.settings)
        
        # Initialize or connect to index
        self._ensure_index()
        self.vector_store = self._create_vector_store()
        
        logger.info(
            "PineconeVectorStoreManager initialized",
            index_name=self.settings.pinecone_index_name,
        )

    def _ensure_index(self) -> None:
        """Ensure the Pinecone index exists, create if not."""
        index_name = self.settings.pinecone_index_name
        
        # List existing indexes
        existing_indexes = [idx.name for idx in self.pinecone.list_indexes()]
        
        if index_name not in existing_indexes:
            logger.info(
                "Creating Pinecone index",
                index_name=index_name,
            )
            
            # Determine dimension based on embedding model
            # text-embedding-ada-002 has 1536 dimensions
            dimension = 1536  # Default for ada-002
            
            # Create index with serverless spec
            self.pinecone.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.settings.pinecone_environment,
                ),
            )
            
            logger.info(
                "Pinecone index created",
                index_name=index_name,
                dimension=dimension,
            )
        else:
            logger.debug(
                "Pinecone index already exists",
                index_name=index_name,
            )

    def _create_vector_store(self) -> PineconeVectorStore:
        """Create LangChain Pinecone vector store wrapper."""
        return PineconeVectorStore.from_existing_index(
            index_name=self.settings.pinecone_index_name,
            embedding=self.embedding_generator.embeddings,
        )

    def add_documents(
        self,
        documents: list[Document],
        namespace: Optional[str] = None,
    ) -> list[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of Document objects to add
            namespace: Optional Pinecone namespace
            
        Returns:
            List of document IDs (chunk IDs)
        """
        try:
            logger.info(
                "Adding documents to vector store",
                num_documents=len(documents),
                namespace=namespace,
            )
            
            # Use LangChain's vector store to add documents
            ids = self.vector_store.add_documents(
                documents=documents,
                namespace=namespace,
            )
            
            logger.info(
                "Documents added to vector store",
                num_documents=len(documents),
                num_ids=len(ids),
                namespace=namespace,
            )
            
            return ids
            
        except Exception as e:
            logger.error(
                "Error adding documents to vector store",
                error=str(e),
                num_documents=len(documents),
            )
            raise ValueError(f"Failed to add documents to vector store: {str(e)}") from e

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        namespace: Optional[str] = None,
        filter: Optional[dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> list[Document]:
        """
        Perform similarity search in the vector store.
        
        Args:
            query: Query text
            k: Number of results to return
            namespace: Optional Pinecone namespace
            filter: Optional metadata filter
            score_threshold: Optional minimum similarity score
            
        Returns:
            List of similar Document objects
        """
        try:
            logger.debug(
                "Performing similarity search",
                query_length=len(query),
                k=k,
                namespace=namespace,
                filter=filter,
            )
            
            # Perform search
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                namespace=namespace,
                filter=filter,
            )
            
            # Filter by score threshold if provided
            if score_threshold is not None:
                results = [(doc, score) for doc, score in results if score >= score_threshold]
            
            # Extract documents only (without scores)
            documents = [doc for doc, score in results]
            
            logger.info(
                "Similarity search completed",
                query_length=len(query),
                num_results=len(documents),
                namespace=namespace,
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Error performing similarity search",
                error=str(e),
                query_length=len(query),
            )
            raise ValueError(f"Failed to perform similarity search: {str(e)}") from e

    def similarity_search_with_scores(
        self,
        query: str,
        k: int = 5,
        namespace: Optional[str] = None,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[tuple[Document, float]]:
        """
        Perform similarity search and return results with scores.
        
        Args:
            query: Query text
            k: Number of results to return
            namespace: Optional Pinecone namespace
            filter: Optional metadata filter
            
        Returns:
            List of tuples (Document, score)
        """
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                namespace=namespace,
                filter=filter,
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Error performing similarity search with scores",
                error=str(e),
                query_length=len(query),
            )
            raise ValueError(f"Failed to perform similarity search: {str(e)}") from e

    def delete_by_metadata(
        self,
        filter: dict[str, Any],
        namespace: Optional[str] = None,
    ) -> None:
        """
        Delete documents from vector store by metadata filter.
        
        Args:
            filter: Metadata filter to match documents
            namespace: Optional Pinecone namespace
        """
        try:
            logger.info(
                "Deleting documents by metadata",
                filter=filter,
                namespace=namespace,
            )
            
            # Get index
            index = self.pinecone.Index(self.settings.pinecone_index_name)
            
            # Delete by metadata filter
            index.delete(filter=filter, namespace=namespace)
            
            logger.info(
                "Documents deleted by metadata",
                filter=filter,
                namespace=namespace,
            )
            
        except Exception as e:
            logger.error(
                "Error deleting documents by metadata",
                error=str(e),
                filter=filter,
            )
            raise ValueError(f"Failed to delete documents: {str(e)}") from e
