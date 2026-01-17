"""RAG query endpoints for historical BRD search."""

from typing import Annotated
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.rag.pipeline import RAGPipeline

router = APIRouter()
logger = structlog.get_logger(__name__)

# Global RAG pipeline instance (initialized lazily)
_rag_pipeline: RAGPipeline | None = None


def get_rag_pipeline(settings: Settings) -> RAGPipeline:
    """Get or create RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline(settings=settings)
    return _rag_pipeline


class RAGSource(BaseModel):
    """Source document reference from RAG retrieval."""

    source: str = Field(..., description="Source document name")
    page: int | None = Field(default=None, description="Page number")
    chunk_index: int | None = Field(default=None, description="Chunk index")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class RAGQueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str = Field(..., description="Natural language query about requirements/BRDs")
    top_k: int | None = Field(default=None, description="Number of results (default from config)")
    filter_document_type: str | None = Field(
        default=None, description="Filter by document type: BRD, SOW, transcript"
    )
    score_threshold: float | None = Field(
        default=None, description="Minimum relevance score (default from config)"
    )


class RAGQueryResponse(BaseModel):
    """Response model for RAG queries."""

    answer: str = Field(..., description="Generated answer based on retrieved context")
    sources: list[RAGSource] = Field(default_factory=list, description="Source documents")
    query: str
    num_sources: int = Field(default=0, description="Number of sources")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")


@router.post("/query", response_model=RAGQueryResponse)
async def query_brd_knowledge(
    request: RAGQueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RAGQueryResponse:
    """
    Query historical BRDs and requirements documents using RAG.

    This endpoint:
    1. Converts the query to an embedding
    2. Searches Pinecone for similar document chunks
    3. Passes relevant context to GPT-4
    4. Returns an answer with source attribution

    Useful for:
    - Finding similar requirements from past projects
    - Checking how issues were resolved before
    - Understanding business context from historical docs
    """
    try:
        rag_pipeline = get_rag_pipeline(settings)

        # Build filter if document type specified
        filter_dict = None
        if request.filter_document_type:
            filter_dict = {"document_type": request.filter_document_type}

        # Query RAG pipeline
        result = rag_pipeline.query(
            question=request.query,
            k=request.top_k,
            filter=filter_dict,
        )

        # Convert sources to API format
        sources = [
            RAGSource(
                source=src.get("source", "unknown"),
                page=src.get("page"),
                chunk_index=src.get("chunk_index"),
                score=src.get("score", 0.0),
            )
            for src in result.get("sources", [])
        ]

        # Calculate confidence (average of source scores)
        confidence = (
            sum(src.score for src in sources) / len(sources) if sources else 0.0
        )

        return RAGQueryResponse(
            answer=result.get("answer", ""),
            sources=sources,
            query=result.get("question", request.query),
            num_sources=result.get("num_sources", len(sources)),
            confidence=confidence,
        )

    except Exception as e:
        logger.error(
            "Error in RAG query",
            error=str(e),
            query=request.query[:100],
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process RAG query: {str(e)}",
        ) from e


@router.post("/similar")
async def find_similar_requirements(
    requirement_text: str,
    top_k: int = 5,
    settings: Annotated[Settings, Depends(get_settings)] = Depends(get_settings),
) -> dict:
    """Find similar requirements from the indexed knowledge base."""
    logger.info("Finding similar requirements", text_length=len(requirement_text))

    try:
        rag_pipeline = get_rag_pipeline(settings)

        # Find similar requirements
        similar = rag_pipeline.find_similar_requirements(
            requirement_text=requirement_text,
            k=top_k,
        )

        return {
            "query": requirement_text,
            "similar_requirements": similar,
            "status": "completed",
        }

    except Exception as e:
        logger.error(
            "Error finding similar requirements",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar requirements: {str(e)}",
        ) from e


@router.get("/stats")
async def get_rag_stats(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Get statistics about the RAG knowledge base."""
    try:
        # Get index stats from Pinecone (simplified)
        from src.vectorstore.pinecone_store import PineconeVectorStoreManager

        vector_store = PineconeVectorStoreManager(settings=settings)
        index = vector_store.pinecone.Index(settings.pinecone_index_name)

        stats = index.describe_index_stats()

        # Extract stats
        vector_count = stats.get("total_vector_count", 0) if isinstance(stats, dict) else 0
        dimension = stats.get("dimension", 1536) if isinstance(stats, dict) else 1536
        fullness = stats.get("index_fullness", 0.0) if isinstance(stats, dict) else 0.0

        return {
            "index_name": settings.pinecone_index_name,
            "total_vectors": vector_count,
            "dimension": dimension,
            "index_fullness": fullness,
        }

    except Exception as e:
        logger.error(
            "Error getting RAG stats",
            error=str(e),
        )
        return {
            "index_name": settings.pinecone_index_name,
            "total_vectors": 0,
            "dimension": 0,
            "index_fullness": 0.0,
            "error": str(e),
        }
