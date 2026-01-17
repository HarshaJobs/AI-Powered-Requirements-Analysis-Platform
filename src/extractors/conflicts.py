"""Conflict detection between requirements."""

import json
from typing import Optional, Any

import structlog
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

from src.config import Settings, get_settings
from src.prompts.conflicts import ConflictDetectionPrompts

logger = structlog.get_logger(__name__)


class Conflict(BaseModel):
    """Pydantic model for a requirement conflict."""

    requirement_1_id: str = Field(..., description="First requirement ID")
    requirement_2_id: str = Field(..., description="Second requirement ID")
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(..., description="Severity: high, medium, or low")
    description: str = Field(..., description="Detailed conflict description")
    recommendation: str = Field(..., description="Recommended resolution approach")
    has_conflict: bool = Field(default=True, description="Whether conflict exists")

    @field_validator("conflict_type")
    @classmethod
    def validate_conflict_type(cls, v: str) -> str:
        """Validate conflict type."""
        valid_types = ["logical", "resource", "temporal", "overlap", "design", "none"]
        v_lower = v.lower()
        if v_lower not in valid_types:
            logger.warning(
                "Unknown conflict type, using 'logical'",
                provided=v,
            )
            return "logical"
        return v_lower

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity."""
        v = v.lower()
        if v not in ["high", "medium", "low"]:
            logger.warning(
                "Invalid severity, using 'medium'",
                provided=v,
            )
            return "medium"
        return v


class ConflictDetector:
    """
    Detect conflicts between requirements using LLM analysis.
    
    Identifies logical contradictions, resource conflicts, temporal conflicts,
    functional overlaps, and design conflicts.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the conflict detector."""
        self.settings = settings or get_settings()
        self.llm = ChatOpenAI(
            model_name=self.settings.openai_model,
            temperature=0.0,  # Deterministic conflict detection
            openai_api_key=self.settings.openai_api_key,
        )
        self.prompts = ConflictDetectionPrompts()
        
        logger.info(
            "ConflictDetector initialized",
            model=self.settings.openai_model,
        )

    def detect_pairwise_conflict(
        self,
        requirement1: str,
        requirement2: str,
        req1_id: Optional[str] = None,
        req2_id: Optional[str] = None,
    ) -> Conflict:
        """
        Detect conflict between two requirements.
        
        Args:
            requirement1: First requirement text
            requirement2: Second requirement text
            req1_id: Optional ID for first requirement
            req2_id: Optional ID for second requirement
            
        Returns:
            Conflict object (has_conflict may be False if no conflict)
        """
        try:
            logger.info(
                "Detecting pairwise conflict",
                req1_id=req1_id,
                req2_id=req2_id,
            )
            
            prompt = self.prompts.get_pairwise_conflict_prompt(
                requirement1=requirement1,
                requirement2=requirement2,
                req1_id=req1_id,
                req2_id=req2_id,
            )
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            conflict_data = self._parse_conflict_response(response_text)
            conflict_data["requirement_1_id"] = req1_id or "REQ-1"
            conflict_data["requirement_2_id"] = req2_id or "REQ-2"
            
            conflict = Conflict(**conflict_data)
            
            logger.info(
                "Pairwise conflict detection completed",
                req1_id=req1_id,
                req2_id=req2_id,
                has_conflict=conflict.has_conflict,
                severity=conflict.severity if conflict.has_conflict else None,
            )
            
            return conflict
            
        except Exception as e:
            logger.error(
                "Error detecting pairwise conflict",
                error=str(e),
                req1_id=req1_id,
                req2_id=req2_id,
            )
            raise ValueError(f"Failed to detect conflict: {str(e)}") from e

    def detect_batch_conflicts(
        self,
        requirements: list[dict[str, str]],
    ) -> list[Conflict]:
        """
        Detect conflicts across multiple requirements.
        
        Args:
            requirements: List of requirement dicts with 'id' and 'text'
            
        Returns:
            List of Conflict objects
        """
        try:
            logger.info(
                "Detecting batch conflicts",
                num_requirements=len(requirements),
            )
            
            prompt = self.prompts.get_batch_conflict_prompt(requirements)
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON array response
            conflicts_data = self._parse_conflict_response(response_text, is_array=True)
            
            conflicts = []
            for conflict_data in conflicts_data:
                try:
                    conflict = Conflict(**conflict_data)
                    conflicts.append(conflict)
                except Exception as e:
                    logger.warning(
                        "Failed to parse conflict",
                        error=str(e),
                        data=conflict_data,
                    )
                    continue
            
            logger.info(
                "Batch conflict detection completed",
                num_conflicts=len(conflicts),
            )
            
            return conflicts
            
        except Exception as e:
            logger.error(
                "Error in batch conflict detection",
                error=str(e),
                num_requirements=len(requirements),
            )
            raise ValueError(f"Failed to detect batch conflicts: {str(e)}") from e

    def classify_severity(
        self,
        conflict_description: str,
        conflict_type: str,
    ) -> str:
        """
        Classify conflict severity.
        
        Args:
            conflict_description: Description of the conflict
            conflict_type: Type of conflict
            
        Returns:
            Severity level: "high", "medium", or "low"
        """
        try:
            prompt = self.prompts.get_severity_classification_prompt(
                conflict_description=conflict_description,
                conflict_type=conflict_type,
            )
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract severity
            severity = response_text.strip().lower()
            if severity not in ["high", "medium", "low"]:
                logger.warning(
                    "Invalid severity returned, using 'medium'",
                    returned=severity,
                )
                return "medium"
            
            logger.debug(
                "Severity classified",
                severity=severity,
            )
            
            return severity
            
        except Exception as e:
            logger.warning(
                "Error classifying severity, using default",
                error=str(e),
            )
            return "medium"  # Default to medium

    def _parse_conflict_response(
        self,
        response_text: str,
        is_array: bool = False,
    ) -> dict | list[dict]:
        """Parse LLM response into conflict data."""
        try:
            json_text = self._extract_json_from_response(response_text)
            data = json.loads(json_text)
            
            if is_array:
                if not isinstance(data, list):
                    data = [data] if data else []
            else:
                if isinstance(data, list):
                    data = data[0] if data else {}
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON in conflict response",
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
