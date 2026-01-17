"""Requirements extraction from transcripts and documents."""

import json
from typing import Optional, Any

import structlog
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

from src.config import Settings, get_settings
from src.prompts.extraction import RequirementsExtractionPrompts

logger = structlog.get_logger(__name__)


class Requirement(BaseModel):
    """Pydantic model for a requirement."""

    id: str = Field(..., description="Unique requirement identifier")
    type: str = Field(..., description="Requirement type: functional or non-functional")
    description: str = Field(..., description="Clear requirement statement")
    priority: str = Field(..., description="Priority: high, medium, or low")
    source_quote: str = Field(..., description="Source quote or paraphrase")
    stakeholder: str = Field(default="", description="Stakeholder who mentioned this")
    needs_clarification: bool = Field(
        default=False,
        description="Whether requirement needs clarification",
    )
    category: Optional[str] = Field(default=None, description="Specific category")
    document_source: Optional[int] = Field(default=None, description="Document number for batch extraction")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate requirement type."""
        v = v.lower()
        if v not in ["functional", "non-functional"]:
            raise ValueError(f"Type must be 'functional' or 'non-functional', got: {v}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority."""
        v = v.lower()
        if v not in ["high", "medium", "low"]:
            raise ValueError(f"Priority must be 'high', 'medium', or 'low', got: {v}")
        return v


class RequirementsExtractor:
    """
    Extract requirements from meeting transcripts and documents using LLM.
    
    Uses structured output parsing with Pydantic models for reliable extraction.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the requirements extractor."""
        self.settings = settings or get_settings()
        self.llm = ChatOpenAI(
            model_name=self.settings.openai_model,
            temperature=0.0,  # Deterministic extraction
            openai_api_key=self.settings.openai_api_key,
        )
        self.prompts = RequirementsExtractionPrompts()
        
        logger.info(
            "RequirementsExtractor initialized",
            model=self.settings.openai_model,
        )

    def extract_from_transcript(
        self,
        transcript: str,
        additional_context: Optional[str] = None,
    ) -> list[Requirement]:
        """
        Extract requirements from a meeting transcript.
        
        Args:
            transcript: Meeting transcript text
            additional_context: Optional project or domain context
            
        Returns:
            List of extracted Requirement objects
        """
        try:
            logger.info(
                "Extracting requirements from transcript",
                transcript_length=len(transcript),
            )
            
            # Get extraction prompt
            prompt = self.prompts.get_extraction_prompt(
                transcript=transcript,
                additional_context=additional_context,
            )
            
            # Call LLM
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            requirements = self._parse_extraction_response(response_text)
            
            logger.info(
                "Requirements extracted",
                num_requirements=len(requirements),
            )
            
            return requirements
            
        except Exception as e:
            logger.error(
                "Error extracting requirements",
                error=str(e),
                transcript_length=len(transcript),
            )
            raise ValueError(f"Failed to extract requirements: {str(e)}") from e

    def batch_extract(
        self,
        documents: list[str],
        additional_context: Optional[str] = None,
    ) -> list[Requirement]:
        """
        Extract requirements from multiple documents in batch.
        
        Args:
            documents: List of document texts
            additional_context: Optional project or domain context
            
        Returns:
            List of extracted Requirement objects
        """
        try:
            logger.info(
                "Batch extracting requirements",
                num_documents=len(documents),
            )
            
            # Get batch extraction prompt
            prompt = self.prompts.get_batch_extraction_prompt(
                documents=documents,
                additional_context=additional_context,
            )
            
            # Call LLM
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            requirements = self._parse_extraction_response(response_text)
            
            logger.info(
                "Batch extraction completed",
                num_requirements=len(requirements),
            )
            
            return requirements
            
        except Exception as e:
            logger.error(
                "Error in batch extraction",
                error=str(e),
                num_documents=len(documents),
            )
            raise ValueError(f"Failed to batch extract requirements: {str(e)}") from e

    def categorize_requirement(
        self,
        requirement_text: str,
    ) -> dict[str, Any]:
        """
        Categorize a single requirement (type, category, priority).
        
        Args:
            requirement_text: Requirement text to categorize
            
        Returns:
            Dictionary with type, category, and priority
        """
        try:
            prompt = self.prompts.get_categorization_prompt(requirement_text)
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            categorization = json.loads(self._extract_json_from_response(response_text))
            
            logger.debug(
                "Requirement categorized",
                requirement_length=len(requirement_text),
                categorization=categorization,
            )
            
            return categorization
            
        except Exception as e:
            logger.error(
                "Error categorizing requirement",
                error=str(e),
            )
            raise ValueError(f"Failed to categorize requirement: {str(e)}") from e

    def _parse_extraction_response(self, response_text: str) -> list[Requirement]:
        """
        Parse LLM response into Requirement objects.
        
        Args:
            response_text: LLM response text (should contain JSON)
            
        Returns:
            List of Requirement objects
        """
        try:
            # Extract JSON from response (may be wrapped in markdown code blocks)
            json_text = self._extract_json_from_response(response_text)
            
            # Parse JSON
            data = json.loads(json_text)
            
            # Ensure it's a list
            if not isinstance(data, list):
                data = [data]
            
            # Convert to Requirement objects
            requirements = []
            for item in data:
                try:
                    req = Requirement(**item)
                    requirements.append(req)
                except Exception as e:
                    logger.warning(
                        "Failed to parse requirement",
                        item=item,
                        error=str(e),
                    )
                    continue
            
            return requirements
            
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON in extraction response",
                error=str(e),
                response_preview=response_text[:200],
            )
            raise ValueError(f"Failed to parse JSON from response: {str(e)}") from e

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from LLM response (may be wrapped in markdown code blocks).
        
        Args:
            response_text: LLM response text
            
        Returns:
            Extracted JSON string
        """
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
        if start == -1:
            start = response_text.find("{")
        
        if start != -1:
            # Find matching closing bracket/brace
            bracket = response_text[start]
            closing = "]" if bracket == "[" else "}"
            
            depth = 0
            for i in range(start, len(response_text)):
                if response_text[i] == bracket:
                    depth += 1
                elif response_text[i] == closing:
                    depth -= 1
                    if depth == 0:
                        return response_text[start:i+1]
        
        # Return as-is if no JSON structure found
        return response_text.strip()
