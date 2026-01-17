"""Reranking pipeline for retrieved documents."""

from typing import Optional

import structlog
from langchain_core.documents import Document

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class Reranker:
    """
    Reranker for retrieved documents using cross-encoder or LLM-based scoring.
    
    Reorders initial retrieval results for better relevance.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the reranker."""
        self.settings = settings or get_settings()
        
        # For now, use LLM-based reranking (can be replaced with cross-encoder)
        self._use_llm_reranking = True
        
        logger.info("Reranker initialized")

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: Optional[int] = None,
    ) -> list[Document]:
        """
        Rerank documents based on relevance to query.
        
        Args:
            query: Query text
            documents: List of documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            Reranked list of Document objects
        """
        if not documents:
            return []
        
        if len(documents) == 1:
            return documents
        
        try:
            if self._use_llm_reranking:
                # LLM-based relevance scoring
                scored_docs = self._llm_rerank(query, documents)
            else:
                # Simple keyword overlap scoring (fallback)
                scored_docs = self._keyword_rerank(query, documents)
            
            # Sort by score and return top k
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            reranked = [doc for doc, score in scored_docs]
            
            if top_k:
                reranked = reranked[:top_k]
            
            logger.debug(
                "Reranking completed",
                query_length=len(query),
                num_documents=len(documents),
                top_k=top_k or len(reranked),
            )
            
            return reranked
            
        except Exception as e:
            logger.warning(
                "Error in reranking, returning original order",
                error=str(e),
            )
            return documents[:top_k] if top_k else documents

    def _keyword_rerank(
        self,
        query: str,
        documents: list[Document],
    ) -> list[tuple[Document, float]]:
        """Simple keyword-based reranking."""
        query_terms = set(query.lower().split())
        scored = []
        
        for doc in documents:
            doc_terms = set(doc.page_content.lower().split())
            
            # Calculate overlap ratio
            overlap = len(query_terms & doc_terms)
            total_terms = len(query_terms | doc_terms)
            score = overlap / total_terms if total_terms > 0 else 0.0
            
            scored.append((doc, score))
        
        return scored

    def _llm_rerank(
        self,
        query: str,
        documents: list[Document],
    ) -> list[tuple[Document, float]]:
        """
        LLM-based reranking using relevance scoring.
        
        Uses prompt to score relevance (0-1) for each document.
        """
        # For now, use simple keyword scoring as LLM reranking requires multiple API calls
        # TODO: Implement proper LLM-based reranking with batch scoring
        return self._keyword_rerank(query, documents)
