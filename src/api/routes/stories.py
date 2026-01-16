"""User story generation endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings

router = APIRouter()
logger = structlog.get_logger(__name__)


class UserStory(BaseModel):
    """JIRA-formatted user story model."""
    
    title: str = Field(..., description="Concise, action-oriented title")
    description: str = Field(..., description="As a [role], I want [feature], so that [benefit]")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Given/When/Then format criteria"
    )
    story_points: int | None = Field(default=None, description="Estimate: 1, 2, 3, 5, 8, 13")
    labels: list[str] = Field(default_factory=list, description="Suggested labels")
    epic_suggestion: str | None = Field(default=None, description="Suggested parent epic")
    technical_notes: str | None = Field(default=None, description="Implementation notes")


class StoryGenerationRequest(BaseModel):
    """Request model for user story generation."""
    
    input_text: str = Field(..., description="Plain text input or requirement to convert")
    requirement_id: str | None = Field(
        default=None, description="Optional: Link to extracted requirement"
    )
    target_role: str | None = Field(
        default=None, description="Target user role (e.g., 'product manager')"
    )
    include_technical_notes: bool = Field(
        default=True, description="Include technical implementation notes"
    )


class StoryGenerationResponse(BaseModel):
    """Response model for user story generation."""
    
    stories: list[UserStory]
    source_text: str
    generation_notes: str | None = None


@router.post("/generate", response_model=StoryGenerationResponse)
async def generate_user_stories(
    request: StoryGenerationRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StoryGenerationResponse:
    """
    Generate JIRA-formatted user stories from plain text input.
    
    Creates stories in the format:
    - "As a [role], I want [feature], so that [benefit]"
    - Includes acceptance criteria in Given/When/Then format
    - Suggests story points based on complexity
    - Recommends labels and epic groupings
    """
    logger.info(
        "Generating user stories",
        input_length=len(request.input_text),
        requirement_id=request.requirement_id,
    )
    
    # TODO: Implement actual story generation using LangChain
    # - Apply story generation prompt template
    # - Parse structured output
    # - Link to requirement if provided
    
    return StoryGenerationResponse(
        stories=[],
        source_text=request.input_text,
        generation_notes="Story generation pending implementation",
    )


@router.post("/from-requirements")
async def generate_stories_from_requirements(
    requirement_ids: list[str],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Generate user stories from extracted requirements."""
    logger.info("Generating stories from requirements", count=len(requirement_ids))
    
    # TODO: Fetch requirements and generate stories for each
    
    return {
        "requirement_count": len(requirement_ids),
        "stories": [],
        "status": "pending",
    }


@router.get("/templates")
async def get_story_templates() -> dict:
    """Get available story templates and formats."""
    return {
        "templates": [
            {
                "name": "standard",
                "format": "As a [role], I want [feature], so that [benefit]",
            },
            {
                "name": "technical",
                "format": "As a [role], I need [capability], because [reason]",
            },
        ],
        "acceptance_criteria_formats": ["given_when_then", "bullet_points", "checklist"],
    }
