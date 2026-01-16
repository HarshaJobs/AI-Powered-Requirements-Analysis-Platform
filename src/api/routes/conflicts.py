"""Conflict detection endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings

router = APIRouter()
logger = structlog.get_logger(__name__)


class Conflict(BaseModel):
    """Detected requirement conflict model."""
    
    conflict_id: str = Field(..., description="Unique conflict ID (e.g., CONF-001)")
    type: str = Field(
        ..., 
        description="direct_contradiction, resource, dependency, priority, scope_overlap"
    )
    severity: str = Field(..., description="critical, high, medium, low")
    requirement_ids: list[str] = Field(..., description="IDs of conflicting requirements")
    description: str = Field(..., description="Description of the conflict")
    evidence: str | None = Field(default=None, description="Supporting evidence from documents")
    resolution_suggestion: str | None = Field(default=None, description="Suggested resolution")


class ConflictAnalysisRequest(BaseModel):
    """Request model for conflict analysis."""
    
    requirement_ids: list[str] | None = Field(
        default=None, description="Specific requirements to analyze"
    )
    document_ids: list[str] | None = Field(
        default=None, description="Documents to include in analysis"
    )
    include_rag_context: bool = Field(
        default=True, description="Include historical BRD context from RAG"
    )
    document_type: str | None = Field(
        default=None, description="Filter by document type: SOW, email, BRD, etc."
    )


class ConflictAnalysisResponse(BaseModel):
    """Response model for conflict analysis."""
    
    conflicts: list[Conflict]
    analysis_notes: str | None = None
    document_type_performance: str | None = Field(
        default=None, description="Notes on accuracy by document type"
    )
    requirements_analyzed: int = 0


@router.post("/analyze", response_model=ConflictAnalysisResponse)
async def analyze_conflicts(
    request: ConflictAnalysisRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConflictAnalysisResponse:
    """
    Analyze requirements for potential conflicts.
    
    Detects:
    - Direct contradictions (logically incompatible requirements)
    - Resource conflicts (competing for same resources)
    - Dependency conflicts (circular or impossible dependencies)
    - Priority conflicts (conflicting business priorities)
    - Scope overlap (duplicate functionality)
    
    Uses RAG to cross-reference with historical BRDs for context.
    Note: Works better on structured SOWs than free-form emails.
    """
    logger.info(
        "Analyzing conflicts",
        requirement_ids=request.requirement_ids,
        document_ids=request.document_ids,
        include_rag=request.include_rag_context,
    )
    
    # TODO: Implement conflict detection using LangChain
    # - Fetch requirements by IDs
    # - Optionally retrieve RAG context from historical BRDs
    # - Apply conflict detection prompt
    # - Parse and return structured conflicts
    
    return ConflictAnalysisResponse(
        conflicts=[],
        analysis_notes="Conflict analysis pending implementation",
        document_type_performance=None,
        requirements_analyzed=0,
    )


@router.post("/cross-document")
async def analyze_cross_document_conflicts(
    document_ids: list[str],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Analyze conflicts across multiple documents."""
    logger.info("Cross-document conflict analysis", document_count=len(document_ids))
    
    return {
        "document_count": len(document_ids),
        "conflicts": [],
        "status": "pending",
    }


@router.get("/types")
async def get_conflict_types() -> dict:
    """Get description of conflict types and severities."""
    return {
        "conflict_types": [
            {
                "type": "direct_contradiction",
                "description": "Requirements that logically cannot coexist",
            },
            {
                "type": "resource",
                "description": "Competing for same resources/constraints",
            },
            {
                "type": "dependency",
                "description": "Circular or impossible dependencies",
            },
            {
                "type": "priority",
                "description": "Conflicting business priorities",
            },
            {
                "type": "scope_overlap",
                "description": "Duplicate or overlapping functionality",
            },
        ],
        "severity_levels": ["critical", "high", "medium", "low"],
    }
