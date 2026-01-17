"""Document upload and management endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel

from src.config import Settings, get_settings
from src.document_processing.pipeline import DocumentProcessingPipeline
from src.vectorstore.pinecone_store import PineconeVectorStoreManager

router = APIRouter()
logger = structlog.get_logger(__name__)

# In-memory document storage (TODO: Replace with persistent storage)
_document_storage: dict[str, bytes] = {}


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: str
    filename: str
    size_bytes: int
    status: str
    message: str


class DocumentIndexRequest(BaseModel):
    """Request model for indexing documents."""

    document_ids: list[str]
    force_reindex: bool = False


class DocumentIndexResponse(BaseModel):
    """Response model for document indexing."""

    indexed_count: int
    chunk_count: int
    status: str


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF or text document to upload")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentUploadResponse:
    """
    Upload a document (PDF or text) for processing.

    Supports:
    - Confluence PDF exports
    - Meeting transcripts (TXT)
    - BRD documents (PDF)
    """
    # Validate file type
    allowed_types = ["application/pdf", "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {allowed_types}",
        )

    # Validate file size
    max_size = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # Generate document ID
    import hashlib

    doc_id = hashlib.sha256(content).hexdigest()[:16]

    # Store document in memory
    _document_storage[doc_id] = content

    logger.info(
        "Document uploaded",
        document_id=doc_id,
        filename=file.filename,
        size=len(content),
    )

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename or "unknown",
        size_bytes=len(content),
        status="uploaded",
        message="Document uploaded successfully. Ready for indexing.",
    )


@router.post("/index", response_model=DocumentIndexResponse)
async def index_documents(
    request: DocumentIndexRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentIndexResponse:
    """
    Index uploaded documents into Pinecone vector store.

    This will:
    1. Load and parse the documents
    2. Chunk into 512-token segments with 50-token overlap
    3. Generate embeddings using OpenAI
    4. Store in Pinecone with metadata
    """
    logger.info(
        "Indexing documents",
        document_ids=request.document_ids,
        force_reindex=request.force_reindex,
    )

    try:
        # Initialize processors
        pipeline = DocumentProcessingPipeline(settings=settings)
        vector_store = PineconeVectorStoreManager(settings=settings)

        total_chunks = 0
        indexed_count = 0

        for doc_id in request.document_ids:
            # Retrieve document from storage
            if doc_id not in _document_storage:
                logger.warning(
                    "Document not found in storage",
                    document_id=doc_id,
                )
                continue

            content = _document_storage[doc_id]
            filename = f"doc_{doc_id}"

            # Determine content type
            content_type = "application/pdf" if content.startswith(b"%PDF") else "text/plain"

            try:
                # Process document: load, preprocess, chunk
                chunks, processing_metadata = pipeline.process_document(
                    content=content,
                    filename=filename,
                    content_type=content_type,
                    document_id=doc_id,
                )

                # Delete existing vectors if force reindex
                if request.force_reindex:
                    vector_store.delete_by_metadata(
                        filter={"document_id": doc_id},
                    )

                # Add chunks to vector store
                vector_store.add_documents(chunks)

                total_chunks += len(chunks)
                indexed_count += 1

                logger.info(
                    "Document indexed",
                    document_id=doc_id,
                    chunk_count=len(chunks),
                )

            except Exception as e:
                logger.error(
                    "Error indexing document",
                    document_id=doc_id,
                    error=str(e),
                )
                continue

        return DocumentIndexResponse(
            indexed_count=indexed_count,
            chunk_count=total_chunks,
            status="completed" if indexed_count > 0 else "failed",
        )

    except Exception as e:
        logger.error(
            "Error in indexing pipeline",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index documents: {str(e)}",
        ) from e


@router.get("/list")
async def list_documents() -> dict:
    """List all uploaded documents."""
    documents = [
        {
            "document_id": doc_id,
            "size_bytes": len(content),
        }
        for doc_id, content in _document_storage.items()
    ]

    return {
        "documents": documents,
        "total": len(documents),
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Delete a document and its vectors from the system."""
    logger.info("Deleting document", document_id=document_id)

    try:
        # Remove from storage
        if document_id in _document_storage:
            del _document_storage[document_id]

        # Remove from Pinecone
        try:
            vector_store = PineconeVectorStoreManager(settings=settings)
            vector_store.delete_by_metadata(filter={"document_id": document_id})
        except Exception as e:
            logger.warning(
                "Error deleting from Pinecone",
                document_id=document_id,
                error=str(e),
            )

        return {
            "document_id": document_id,
            "status": "deleted",
        }

    except Exception as e:
        logger.error(
            "Error deleting document",
            document_id=document_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}",
        ) from e
