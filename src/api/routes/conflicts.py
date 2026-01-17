"""Conflict detection endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.extractors.conflicts import ConflictDetector
from src.api.routes.extraction import _requirement_storage

router = APIRouter()
logger = structlog.get_logger(__name__)


class Conflict(BaseModel):
    """Detected requirement conflict model."""

    requirement_1_id: str = Field(..., description="First requirement ID")
    requirement_2_id: str = Field(..., description="Second requirement ID")
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(..., description="high, medium, or low")
    description: str = Field(..., description="Description of the conflict")
    recommendation: str = Field(..., description="Recommended resolution approach")
    has_conflict: bool = Field(default=True, description="Whether conflict exists")


class ConflictAnalysisRequest(BaseModel):
    """Request model for conflict analysis."""

    requirement_ids: list[str] | None = Field(
        default=None, description="Specific requirements to analyze"
    )
    analyze_all: bool = Field(default=False, description="Analyze all stored requirements")


class ConflictAnalysisResponse(BaseModel):
    """Response model for conflict analysis."""

    conflicts: list[Conflict]
    analysis_notes: str | None = None
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
    """
    logger.info(
        "Analyzing conflicts",
        requirement_ids=request.requirement_ids,
        analyze_all=request.analyze_all,
    )

    try:
        detector = ConflictDetector(settings=settings)

        # Determine which requirements to analyze
        if request.analyze_all:
            requirement_ids = list(_requirement_storage.keys())
        elif request.requirement_ids:
            requirement_ids = request.requirement_ids
        else:
            raise HTTPException(
                status_code=400,
                detail="Either requirement_ids or analyze_all must be provided",
            )

        if len(requirement_ids) < 2:
            return ConflictAnalysisResponse(
                conflicts=[],
                analysis_notes="Need at least 2 requirements to detect conflicts",
                requirements_analyzed=len(requirement_ids),
            )

        # Fetch requirements
        requirements_list = []
        for req_id in requirement_ids:
            if req_id not in _requirement_storage:
                logger.warning(
                    "Requirement not found",
                    requirement_id=req_id,
                )
                continue
            req_data = _requirement_storage[req_id]
            requirements_list.append(
                {
                    "id": req_id,
                    "text": req_data.get("description", ""),
                    "type": req_data.get("type"),
                    "priority": req_data.get("priority"),
                }
            )

        if len(requirements_list) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 valid requirements to analyze",
            )

        # Detect conflicts
        detected_conflicts = detector.detect_batch_conflicts(requirements_list)

        # Convert to API format
        conflicts = [
            Conflict(
                requirement_1_id=conflict.requirement_1_id,
                requirement_2_id=conflict.requirement_2_id,
                conflict_type=conflict.conflict_type,
                severity=conflict.severity,
                description=conflict.description,
                recommendation=conflict.recommendation,
                has_conflict=conflict.has_conflict,
            )
            for conflict in detected_conflicts
            if conflict.has_conflict
        ]

        analysis_notes = f"Analyzed {len(requirements_list)} requirements. Found {len(conflicts)} conflicts: {sum(1 for c in conflicts if c.severity == 'high')} high, {sum(1 for c in conflicts if c.severity == 'medium')} medium, {sum(1 for c in conflicts if c.severity == 'low')} low."

        return ConflictAnalysisResponse(
            conflicts=conflicts,
            analysis_notes=analysis_notes,
            requirements_analyzed=len(requirements_list),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error analyzing conflicts",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze conflicts: {str(e)}",
        ) from e


@router.post("/pairwise")
async def analyze_pairwise_conflict(
    requirement_1_id: str,
    requirement_2_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Conflict:
    """Analyze conflict between two specific requirements."""
    logger.info(
        "Analyzing pairwise conflict",
        req1_id=requirement_1_id,
        req2_id=requirement_2_id,
    )

    try:
        detector = ConflictDetector(settings=settings)

        # Fetch requirements
        if requirement_1_id not in _requirement_storage:
            raise HTTPException(
                status_code=404,
                detail=f"Requirement {requirement_1_id} not found",
            )
        if requirement_2_id not in _requirement_storage:
            raise HTTPException(
                status_code=404,
                detail=f"Requirement {requirement_2_id} not found",
            )

        req1_data = _requirement_storage[requirement_1_id]
        req2_data = _requirement_storage[requirement_2_id]

        req1_text = req1_data.get("description", "")
        req2_text = req2_data.get("description", "")

        # Detect conflict
        conflict = detector.detect_pairwise_conflict(
            requirement1=req1_text,
            requirement2=req2_text,
            req1_id=requirement_1_id,
            req2_id=requirement_2_id,
        )

        # Convert to API format
        return Conflict(
            requirement_1_id=conflict.requirement_1_id,
            requirement_2_id=conflict.requirement_2_id,
            conflict_type=conflict.conflict_type,
            severity=conflict.severity,
            description=conflict.description,
            recommendation=conflict.recommendation,
            has_conflict=conflict.has_conflict,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error analyzing pairwise conflict",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze conflict: {str(e)}",
        ) from e


@router.get("/types")
async def get_conflict_types() -> dict:
    """Get description of conflict types and severities."""
    return {
        "conflict_types": [
            {
                "type": "logical",
                "description": "Requirements that logically cannot coexist",
            },
            {
                "type": "resource",
                "description": "Competing for same resources/constraints",
            },
            {
                "type": "temporal",
                "description": "Conflicting time constraints or sequences",
            },
            {
                "type": "overlap",
                "description": "Duplicate or overlapping functionality",
            },
            {
                "type": "design",
                "description": "Conflicting architectural or design decisions",
            },
        ],
        "severity_levels": ["high", "medium", "low"],
    }
