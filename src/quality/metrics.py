"""Requirements quality metrics and compliance checking."""

from typing import Optional
import re

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class QualityMetrics:
    """
    Calculate quality metrics for requirements.
    
    Metrics:
    - Ambiguity score
    - Completeness score
    - Testability score
    - ISO/IEEE 29148 compliance
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the quality metrics calculator."""
        self.settings = settings or get_settings()
        
        # Ambiguous words/phrases
        self.ambiguous_terms = {
            "fast", "quick", "slow", "efficient", "user-friendly",
            "easy", "simple", "complex", "good", "better", "best",
            "often", "sometimes", "rarely", "soon", "later",
            "flexible", "scalable", "reliable", "robust",
        }
        
        logger.info("QualityMetrics initialized")

    def calculate_quality_score(self, requirement: dict) -> dict:
        """
        Calculate overall quality score for a requirement.
        
        Args:
            requirement: Requirement dictionary with 'description', 'type', etc.
            
        Returns:
            Dictionary with quality metrics and overall score
        """
        description = requirement.get("description", "")
        
        metrics = {
            "ambiguity_score": self.calculate_ambiguity(description),
            "completeness_score": self.calculate_completeness(requirement),
            "testability_score": self.calculate_testability(description),
            "compliance_score": self.check_iso_compliance(requirement),
        }
        
        # Overall quality score (weighted average)
        overall = (
            metrics["ambiguity_score"] * 0.3
            + metrics["completeness_score"] * 0.3
            + metrics["testability_score"] * 0.2
            + metrics["compliance_score"] * 0.2
        )
        
        metrics["overall_score"] = overall
        metrics["quality_grade"] = self._grade_quality(overall)
        
        return metrics

    def calculate_ambiguity(self, description: str) -> float:
        """
        Calculate ambiguity score (0-1, higher = less ambiguous).
        
        Checks for vague terms, unclear references, missing specifics.
        """
        if not description:
            return 0.0
        
        description_lower = description.lower()
        
        # Count ambiguous terms
        ambiguous_count = sum(1 for term in self.ambiguous_terms if term in description_lower)
        
        # Check for unclear references (pronouns without clear referents)
        pronoun_pattern = r"\b(?:it|this|that|they|these|those)\b"
        pronoun_count = len(re.findall(pronoun_pattern, description_lower))
        
        # Normalize by text length
        word_count = len(description.split())
        if word_count == 0:
            return 0.0
        
        ambiguity_ratio = (ambiguous_count * 2 + pronoun_count) / max(word_count, 1)
        
        # Convert to score (0-1, higher = less ambiguous)
        ambiguity_score = max(0.0, 1.0 - min(ambiguity_ratio, 1.0))
        
        return round(ambiguity_score, 3)

    def calculate_completeness(self, requirement: dict) -> float:
        """
        Calculate completeness score (0-1, higher = more complete).
        
        Checks for required fields, sufficient detail.
        """
        required_fields = ["id", "type", "description", "priority"]
        optional_fields = ["source_quote", "stakeholder", "category"]
        
        # Check required fields
        required_present = sum(1 for field in required_fields if requirement.get(field))
        required_score = required_present / len(required_fields)
        
        # Check optional fields (bonus)
        optional_present = sum(1 for field in optional_fields if requirement.get(field))
        optional_score = optional_present / len(optional_fields) * 0.3
        
        completeness = min(1.0, required_score + optional_score)
        
        return round(completeness, 3)

    def calculate_testability(self, description: str) -> float:
        """
        Calculate testability score (0-1, higher = more testable).
        
        Checks for measurable criteria, clear conditions.
        """
        if not description:
            return 0.0
        
        description_lower = description.lower()
        
        # Positive indicators
        measurable_words = ["shall", "must", "will", "when", "if", "then"]
        measurable_count = sum(1 for word in measurable_words if word in description_lower)
        
        # Check for numeric values (indicates specificity)
        numeric_count = len(re.findall(r"\d+", description))
        
        # Check for conditions (if-then patterns)
        condition_count = len(re.findall(r"\b(?:if|when|unless|provided that)\b", description_lower))
        
        # Normalize by text length
        word_count = len(description.split())
        if word_count == 0:
            return 0.0
        
        testability_ratio = (measurable_count + numeric_count * 0.5 + condition_count) / max(word_count, 1)
        testability_score = min(1.0, testability_ratio * 2)
        
        return round(testability_score, 3)

    def check_iso_compliance(self, requirement: dict) -> float:
        """
        Check ISO/IEEE 29148 compliance (0-1, higher = more compliant).
        
        ISO 29148 requirements:
        - Unique identifier
        - Statement (shall/must format)
        - Rationale
        - Acceptance criteria
        """
        description = requirement.get("description", "").lower()
        
        # Check for requirement statement format (shall/must)
        has_statement = bool(re.search(r"\b(?:shall|must|will)\b", description))
        
        # Check for unique ID
        has_id = bool(requirement.get("id"))
        
        # Check for rationale (optional but recommended)
        has_rationale = bool(requirement.get("source_quote") or requirement.get("stakeholder"))
        
        # Check for acceptance criteria (could be in description)
        has_criteria = bool(re.search(r"\b(?:when|if|then|given|expected)\b", description))
        
        # Score calculation
        compliance_score = (
            (has_statement * 0.4)
            + (has_id * 0.3)
            + (has_rationale * 0.2)
            + (has_criteria * 0.1)
        )
        
        return round(compliance_score, 3)

    def _grade_quality(self, score: float) -> str:
        """Convert quality score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
