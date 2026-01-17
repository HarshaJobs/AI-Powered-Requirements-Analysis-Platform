"""Requirements extraction endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.extractors.requirements import RequirementsExtractor
from src.extractors.transcript_processor import TranscriptProcessor

router = APIRouter()
logger = structlog.get_logger(__name__)

# In-memory requirement storage
_requirement_storage: dict[str, dict] = {}


class Requirement(BaseModel):
    """Extracted requirement model."""

    id: str = Field(..., description="Unique requirement ID (e.g., REQ-001)")
    type: str = Field(..., description="functional or non-functional")
    description: str = Field(..., description="Requirement description")
    priority: str = Field(default="medium", description="high, medium, low")
    source_quote: str | None = Field(default=None, description="Original text from document")
    stakeholder: str | None = Field(default=None, description="Stakeholder who mentioned this")
    needs_clarification: bool = Field(default=False)
    category: str | None = Field(default=None, description="Specific category")


class ExtractionRequest(BaseModel):
    """Request model for requirements extraction."""

    document_id: str | None = Field(
        default=None, description="ID of uploaded document to process"
    )
    text: str | None = Field(
        default=None, description="Raw text to extract requirements from"
    )
    context: str | None = Field(default=None, description="Additional context for extraction")


class ExtractionResponse(BaseModel):
    """Response model for requirements extraction."""

    requirements: list[Requirement]
    summary: str
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

    try:
        extractor = RequirementsExtractor(settings=settings)
        processor = TranscriptProcessor()

        # Get text to process
        if request.text:
            transcript = request.text
        elif request.document_id:
            # Load from stored documents (simplified - would need document retrieval)
            raise HTTPException(
                status_code=400,
                detail="Document ID extraction not yet implemented. Please provide text directly.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either document_id or text must be provided",
            )

        # Preprocess transcript
        preprocessed = processor.preprocess_transcript(transcript)

        # Extract requirements
        extracted_reqs = extractor.extract_from_transcript(
            transcript=preprocessed,
            additional_context=request.context,
        )

        # Convert to API format
        requirements = [
            Requirement(
                id=req.id,
                type=req.type,
                description=req.description,
                priority=req.priority,
                source_quote=req.source_quote,
                stakeholder=req.stakeholder,
                needs_clarification=req.needs_clarification,
                category=req.category,
            )
            for req in extracted_reqs
        ]

        # Store requirements
        for req in extracted_reqs:
            _requirement_storage[req.id] = req.model_dump()

        summary = f"Extracted {len(requirements)} requirements: {sum(1 for r in requirements if r.type == 'functional')} functional, {sum(1 for r in requirements if r.type == 'non-functional')} non-functional"

        return ExtractionResponse(
            requirements=requirements,
            summary=summary,
            source_document=request.document_id,
            extraction_notes=f"Extraction completed. {sum(1 for r in requirements if r.needs_clarification)} requirements need clarification.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error extracting requirements",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract requirements: {str(e)}",
        ) from e


@router.post("/batch")
async def batch_extract_requirements(
    document_ids: list[str],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Extract requirements from multiple documents."""
    logger.info("Batch extraction", document_count=len(document_ids))

    # TODO: Implement batch processing with document loading
    # For now, return status

    return {
        "job_id": f"batch-{len(document_ids)}",
        "document_count": len(document_ids),
        "status": "queued",
        "message": "Batch extraction not yet implemented. Use /requirements endpoint for single extractions.",
    }


@router.get("/requirements/{requirement_id}")
async def get_requirement(requirement_id: str) -> Requirement:
    """Get a stored requirement by ID."""
    if requirement_id not in _requirement_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Requirement {requirement_id} not found",
        )

    req_data = _requirement_storage[requirement_id]
    return Requirement(**req_data)


@router.get("/requirements")
async def list_requirements() -> dict:
    """List all extracted requirements."""
    requirements = [
        Requirement(**req_data) for req_data in _requirement_storage.values()
    ]

    return {
        "requirements": requirements,
        "total": len(requirements),
    }
