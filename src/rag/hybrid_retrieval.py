"""Hybrid retrieval combining vector and keyword search."""

from typing import Optional, Any
from collections import Counter

import structlog
from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.vectorstore.pinecone_store import PineconeVectorStoreManager

logger = structlog.get_logger(__name__)


class HybridRetriever:
    """
    Hybrid retriever combining vector (semantic) and keyword (BM25) search.
    
    Uses reciprocal rank fusion (RRF) to combine results from both methods.
    """

    def __init__(
        self,
        vector_store: Optional[PineconeVectorStoreManager] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize the hybrid retriever."""
        self.settings = settings or get_settings()
        self.vector_store = vector_store or PineconeVectorStoreManager(settings=self.settings)
        
        # Simple BM25 keyword index (in-memory)
        self._keyword_index: dict[str, dict] = {}
        self._document_map: dict[str, Document] = {}
        
        logger.info("HybridRetriever initialized")

    def add_documents(self, documents: list[Document]) -> None:
        """Build keyword index from documents."""
        from collections import defaultdict
        
        # Simple term frequency indexing
        for doc in documents:
            doc_id = doc.metadata.get("chunk_id", doc.metadata.get("source", ""))
            self._document_map[doc_id] = doc
            
            # Tokenize text
            terms = doc.page_content.lower().split()
            term_freq = Counter(terms)
            
            if doc_id not in self._keyword_index:
                self._keyword_index[doc_id] = {"tf": dict(term_freq), "length": len(terms)}

    def retrieve(
        self,
        query: str,
        k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[Document]:
        """
        Retrieve documents using hybrid retrieval with RRF.
        
        Args:
            query: Query text
            k: Number of results to return
            vector_weight: Weight for vector search results
            keyword_weight: Weight for keyword search results
            filter: Optional metadata filter
            
        Returns:
            List of retrieved Document objects
        """
        try:
            # Vector retrieval
            vector_docs = self.vector_store.similarity_search_with_scores(
                query=query,
                k=k * 2,  # Get more candidates for reranking
                filter=filter,
            )
            
            # Keyword retrieval (simple BM25-like scoring)
            keyword_scores = self._keyword_search(query, k * 2)
            
            # Combine using reciprocal rank fusion
            combined = self._reciprocal_rank_fusion(
                vector_results=vector_docs,
                keyword_results=keyword_scores,
                k=k,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
            )
            
            logger.debug(
                "Hybrid retrieval completed",
                query_length=len(query),
                num_results=len(combined),
            )
            
            return combined
            
        except Exception as e:
            logger.error(
                "Error in hybrid retrieval",
                error=str(e),
            )
            # Fallback to vector-only
            return self.vector_store.similarity_search(query=query, k=k, filter=filter)

    def _keyword_search(self, query: str, k: int) -> list[tuple[str, float]]:
        """Simple keyword-based search with TF-IDF-like scoring."""
        query_terms = query.lower().split()
        scores: dict[str, float] = {}
        
        for doc_id, doc_info in self._keyword_index.items():
            score = 0.0
            doc_tf = doc_info["tf"]
            doc_length = doc_info["length"]
            
            for term in query_terms:
                if term in doc_tf:
                    # Simple TF scoring (normalized by document length)
                    tf = doc_tf[term] / doc_length if doc_length > 0 else 0
                    score += tf
            
            if score > 0:
                scores[doc_id] = score
        
        # Sort by score and return top k
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(doc_id, score) for doc_id, score in sorted_scores[:k]]

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[tuple[Document, float]],
        keyword_results: list[tuple[str, float]],
        k: int,
        vector_weight: float,
        keyword_weight: float,
    ) -> list[Document]:
        """Combine results using weighted reciprocal rank fusion."""
        rrf_scores: dict[str, float] = {}
        
        # Process vector results
        for rank, (doc, score) in enumerate(vector_results, start=1):
            doc_id = doc.metadata.get("chunk_id", doc.metadata.get("source", ""))
            rrf_score = vector_weight / (60 + rank)  # RRF formula
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
        
        # Process keyword results
        for rank, (doc_id, score) in enumerate(keyword_results, start=1):
            rrf_score = keyword_weight / (60 + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
        
        # Get documents in ranked order
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        
        for doc_id, _ in sorted_ids[:k]:
            if doc_id in self._document_map:
                results.append(self._document_map[doc_id])
        
        return results
