"""User story generation endpoints."""

from typing import Annotated
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.extractors.stories import UserStoryGenerator
from src.api.routes.extraction import _requirement_storage, Requirement as ExtractedRequirement

router = APIRouter()
logger = structlog.get_logger(__name__)


class UserStory(BaseModel):
    """JIRA-formatted user story model."""

    title: str = Field(..., description="Concise, action-oriented title")
    description: str = Field(..., description="As a [role], I want [feature], so that [benefit]")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Given/When/Then format criteria"
    )
    story_points: int | None = Field(default=None, description="Estimate: 1, 2, 3, 5, 8, 13, 21")
    labels: list[str] = Field(default_factory=list, description="Suggested labels")
    priority: str = Field(..., description="Priority: High, Medium, Low")
    requirement_id: str | None = Field(default=None, description="Source requirement ID")
    issue_type: str = Field(default="Story", description="JIRA issue type")


class StoryGenerationRequest(BaseModel):
    """Request model for user story generation."""

    input_text: str = Field(..., description="Plain text input or requirement to convert")
    requirement_id: str | None = Field(
        default=None, description="Optional: Link to extracted requirement"
    )
    context: str | None = Field(default=None, description="Additional context for generation")


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

    try:
        generator = UserStoryGenerator(settings=settings)

        # Get requirement type if requirement_id provided
        requirement_type = None
        if request.requirement_id and request.requirement_id in _requirement_storage:
            req_data = _requirement_storage[request.requirement_id]
            requirement_type = req_data.get("type")

        # Generate story
        story = generator.generate_from_requirement(
            requirement_text=request.input_text,
            requirement_id=request.requirement_id,
            requirement_type=requirement_type,
            context=request.context,
        )

        # Convert to API format
        api_story = UserStory(
            title=story.title,
            description=story.description,
            acceptance_criteria=story.acceptance_criteria,
            story_points=story.story_points,
            labels=story.labels,
            priority=story.priority,
            requirement_id=story.requirement_id,
            issue_type=story.issue_type,
        )

        return StoryGenerationResponse(
            stories=[api_story],
            source_text=request.input_text,
            generation_notes=f"Generated story with {len(story.acceptance_criteria)} acceptance criteria and {story.story_points} story points.",
        )

    except Exception as e:
        logger.error(
            "Error generating user story",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate user story: {str(e)}",
        ) from e


@router.post("/from-requirements")
async def generate_stories_from_requirements(
    requirement_ids: list[str],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Generate user stories from extracted requirements."""
    logger.info("Generating stories from requirements", count=len(requirement_ids))

    try:
        generator = UserStoryGenerator(settings=settings)

        # Fetch requirements
        requirements_data = []
        for req_id in requirement_ids:
            if req_id not in _requirement_storage:
                logger.warning(
                    "Requirement not found",
                    requirement_id=req_id,
                )
                continue

            req_data = _requirement_storage[req_id]
            requirements_data.append(req_data)

        if not requirements_data:
            raise HTTPException(
                status_code=404,
                detail="No valid requirements found",
            )

        # Convert to format expected by batch generator
        requirements_list = [
            {
                "id": req.get("id"),
                "text": req.get("description"),
                "type": req.get("type"),
                "priority": req.get("priority"),
            }
            for req in requirements_data
        ]

        # Generate stories
        stories = generator.batch_generate(requirements_list)

        # Convert to API format
        api_stories = [
            UserStory(
                title=story.title,
                description=story.description,
                acceptance_criteria=story.acceptance_criteria,
                story_points=story.story_points,
                labels=story.labels,
                priority=story.priority,
                requirement_id=story.requirement_id,
                issue_type=story.issue_type,
            )
            for story in stories
        ]

        return {
            "requirement_count": len(requirements_data),
            "stories": api_stories,
            "status": "completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error generating stories from requirements",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate stories: {str(e)}",
        ) from e


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
