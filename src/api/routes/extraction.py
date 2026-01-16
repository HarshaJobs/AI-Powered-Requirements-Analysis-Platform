"""Requirements extraction endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings

router = APIRouter()
logger = structlog.get_logger(__name__)


class Requirement(BaseModel):
    """Extracted requirement model."""
    
    id: str = Field(..., description="Unique requirement ID (e.g., REQ-001)")
    type: str = Field(..., description="functional, non-functional, business_rule, constraint")
    description: str = Field(..., description="Requirement description")
    priority: str = Field(default="medium", description="high, medium, low")
    source_quote: str | None = Field(default=None, description="Original text from document")
    stakeholder: str | None = Field(default=None, description="Stakeholder who mentioned this")
    needs_clarification: bool = Field(default=False)
    clarification_notes: str | None = Field(default=None)


class ExtractionRequest(BaseModel):
    """Request model for requirements extraction."""
    
    document_id: str | None = Field(
        default=None, description="ID of uploaded document to process"
    )
    text: str | None = Field(
        default=None, description="Raw text to extract requirements from"
    )
    include_implicit: bool = Field(
        default=True, description="Include implicit/inferred requirements"
    )


class ExtractionResponse(BaseModel):
    """Response model for requirements extraction."""
    
    requirements: list[Requirement]
    summary: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_document: str | None = None
    extraction_notes: str | None = None


@router.post("/requirements", response_model=ExtractionResponse)
async def extract_requirements(
    request: ExtractionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExtractionResponse:
    """
    Extract requirements from a document or text input.
    
    Uses GPT-4 with specialized prompts to identify:
    - Functional requirements
    - Non-functional requirements
    - Business rules
    - Constraints
    
    Each requirement is categorized, prioritized, and linked to source text.
    """
    if not request.document_id and not request.text:
        raise HTTPException(
            status_code=400,
            detail="Either document_id or text must be provided",
        )
    
    logger.info(
        "Extracting requirements",
        document_id=request.document_id,
        text_length=len(request.text) if request.text else 0,
    )
    
    # TODO: Implement actual extraction using LangChain
    # - Load document if document_id provided
    # - Apply extraction prompt template
    # - Parse structured output
    
    # Placeholder response
    return ExtractionResponse(
        requirements=[],
        summary="Extraction pending implementation",
        confidence_score=0.0,
        source_document=request.document_id,
        extraction_notes="Pipeline not yet implemented",
    )


@router.post("/batch")
async def batch_extract_requirements(
    document_ids: list[str],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Extract requirements from multiple documents."""
    logger.info("Batch extraction", document_count=len(document_ids))
    
    # TODO: Implement batch processing
    
    return {
        "job_id": "batch-001",
        "document_count": len(document_ids),
        "status": "queued",
    }
