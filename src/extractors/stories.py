"""User story generation from requirements."""

import json
from typing import Optional

import structlog
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

from src.config import Settings, get_settings
from src.prompts.stories import UserStoryPrompts

logger = structlog.get_logger(__name__)


class UserStory(BaseModel):
    """Pydantic model for a JIRA user story."""

    title: str = Field(..., description="User story title/summary (max 255 chars)", max_length=255)
    description: str = Field(..., description="User story description")
    acceptance_criteria: list[str] = Field(..., description="List of acceptance criteria")
    story_points: int = Field(..., description="Story points estimate (Fibonacci scale)")
    labels: list[str] = Field(default_factory=list, description="JIRA labels/tags")
    priority: str = Field(..., description="Priority: High, Medium, Low")
    issue_type: str = Field(default="Story", description="JIRA issue type")
    requirement_id: Optional[str] = Field(default=None, description="Source requirement ID")

    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int) -> int:
        """Validate story points are in Fibonacci sequence."""
        fibonacci = [1, 2, 3, 5, 8, 13, 21]
        if v not in fibonacci:
            # Round to nearest Fibonacci number
            closest = min(fibonacci, key=lambda x: abs(x - v))
            logger.warning(
                "Story points not in Fibonacci sequence, rounding",
                original=v,
                rounded=closest,
            )
            return closest
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority."""
        v = v.strip()
        # Map common variations
        priority_map = {
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "critical": "Highest",
            "trivial": "Lowest",
        }
        return priority_map.get(v.lower(), v)

    def to_jira_format(self) -> dict:
        """Convert to JIRA API format."""
        return {
            "summary": self.title,
            "description": self._format_jira_description(),
            "issuetype": {"name": self.issue_type},
            "priority": {"name": self.priority},
            "labels": self.labels,
            "customfield_10016": self.story_points,  # Story Points custom field (may vary by instance)
        }

    def _format_jira_description(self) -> str:
        """Format description with acceptance criteria for JIRA."""
        lines = [self.description, "", "*Acceptance Criteria:*", ""]
        for i, criteria in enumerate(self.acceptance_criteria, start=1):
            lines.append(f"# {criteria}")
        return "\n".join(lines)


class UserStoryGenerator:
    """
    Generate user stories from requirements in JIRA format.
    
    Uses LLM to create user stories with acceptance criteria and story point estimates.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the user story generator."""
        self.settings = settings or get_settings()
        self.llm = ChatOpenAI(
            model_name=self.settings.openai_model,
            temperature=0.3,  # Slight creativity for better stories
            openai_api_key=self.settings.openai_api_key,
        )
        self.prompts = UserStoryPrompts()
        
        logger.info(
            "UserStoryGenerator initialized",
            model=self.settings.openai_model,
        )

    def generate_from_requirement(
        self,
        requirement_text: str,
        requirement_id: Optional[str] = None,
        requirement_type: Optional[str] = None,
        context: Optional[str] = None,
    ) -> UserStory:
        """
        Generate a user story from a single requirement.
        
        Args:
            requirement_text: Requirement text
            requirement_id: Optional requirement ID
            requirement_type: Optional requirement type
            context: Optional additional context
            
        Returns:
            UserStory object
        """
        try:
            logger.info(
                "Generating user story from requirement",
                requirement_id=requirement_id,
                requirement_length=len(requirement_text),
            )
            
            prompt = self.prompts.get_story_generation_prompt(
                requirement_text=requirement_text,
                requirement_id=requirement_id,
                requirement_type=requirement_type,
                context=context,
            )
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            story_data = self._parse_story_response(response_text)
            story_data["requirement_id"] = requirement_id
            
            story = UserStory(**story_data)
            
            logger.info(
                "User story generated",
                requirement_id=requirement_id,
                title=story.title,
                story_points=story.story_points,
            )
            
            return story
            
        except Exception as e:
            logger.error(
                "Error generating user story",
                error=str(e),
                requirement_id=requirement_id,
            )
            raise ValueError(f"Failed to generate user story: {str(e)}") from e

    def batch_generate(
        self,
        requirements: list[dict[str, str]],
        context: Optional[str] = None,
    ) -> list[UserStory]:
        """
        Generate user stories from multiple requirements.
        
        Args:
            requirements: List of requirement dicts with 'id', 'text', 'type', 'priority'
            context: Optional additional context
            
        Returns:
            List of UserStory objects
        """
        try:
            logger.info(
                "Batch generating user stories",
                num_requirements=len(requirements),
            )
            
            prompt = self.prompts.get_batch_story_prompt(
                requirements=requirements,
                context=context,
            )
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON array response
            stories_data = self._parse_story_response(response_text, is_array=True)
            
            stories = []
            for i, story_data in enumerate(stories_data):
                try:
                    # Ensure requirement_id is set
                    if "requirement_id" not in story_data and i < len(requirements):
                        story_data["requirement_id"] = requirements[i].get("id")
                    
                    story = UserStory(**story_data)
                    stories.append(story)
                except Exception as e:
                    logger.warning(
                        "Failed to parse user story",
                        index=i,
                        error=str(e),
                        data=story_data,
                    )
                    continue
            
            logger.info(
                "Batch generation completed",
                num_stories=len(stories),
            )
            
            return stories
            
        except Exception as e:
            logger.error(
                "Error in batch generation",
                error=str(e),
                num_requirements=len(requirements),
            )
            raise ValueError(f"Failed to batch generate user stories: {str(e)}") from e

    def estimate_story_points(
        self,
        description: str,
        acceptance_criteria: list[str],
    ) -> int:
        """
        Estimate story points for a user story.
        
        Args:
            description: User story description
            acceptance_criteria: List of acceptance criteria
            
        Returns:
            Story points estimate (Fibonacci scale)
        """
        try:
            prompt = self.prompts.get_story_points_estimation_prompt(
                description=description,
                acceptance_criteria=acceptance_criteria,
            )
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract number from response
            import re
            numbers = re.findall(r'\d+', response_text)
            if numbers:
                story_points = int(numbers[0])
                # Validate and round to Fibonacci
                fibonacci = [1, 2, 3, 5, 8, 13, 21]
                story_points = min(fibonacci, key=lambda x: abs(x - story_points))
                
                logger.debug(
                    "Story points estimated",
                    estimate=story_points,
                )
                
                return story_points
            
            # Default to medium estimate
            return 5
            
        except Exception as e:
            logger.warning(
                "Error estimating story points, using default",
                error=str(e),
            )
            return 5  # Default medium estimate

    def _parse_story_response(
        self,
        response_text: str,
        is_array: bool = False,
    ) -> dict | list[dict]:
        """
        Parse LLM response into story data.
        
        Args:
            response_text: LLM response text
            is_array: Whether response is an array
            
        Returns:
            Story data (dict or list of dicts)
        """
        try:
            json_text = self._extract_json_from_response(response_text)
            data = json.loads(json_text)
            
            if is_array and not isinstance(data, list):
                data = [data]
            elif not is_array and isinstance(data, list):
                data = data[0] if data else {}
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON in story response",
                error=str(e),
                response_preview=response_text[:200],
            )
            raise ValueError(f"Failed to parse JSON from response: {str(e)}") from e

    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from LLM response (may be wrapped in markdown code blocks)."""
        # Remove markdown code blocks if present
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        
        # Try to find JSON array or object
        start = response_text.find("[")
        obj_start = response_text.find("{")
        
        if start != -1 and (obj_start == -1 or start < obj_start):
            # Find matching closing bracket
            depth = 0
            for i in range(start, len(response_text)):
                if response_text[i] == "[":
                    depth += 1
                elif response_text[i] == "]":
                    depth -= 1
                    if depth == 0:
                        return response_text[start:i+1]
        elif obj_start != -1:
            # Find matching closing brace
            depth = 0
            for i in range(obj_start, len(response_text)):
                if response_text[i] == "{":
                    depth += 1
                elif response_text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return response_text[obj_start:i+1]
        
        return response_text.strip()
