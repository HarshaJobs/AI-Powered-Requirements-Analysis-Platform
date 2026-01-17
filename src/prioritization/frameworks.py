"""Prioritization frameworks (MoSCoW, Kano, Weighted Scoring)."""

from typing import Optional
from enum import Enum

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class PriorityCategory(str, Enum):
    """Priority categories for MoSCoW."""
    MUST_HAVE = "must_have"
    SHOULD_HAVE = "should_have"
    COULD_HAVE = "could_have"
    WONT_HAVE = "wont_have"


class KanoCategory(str, Enum):
    """Kano model categories."""
    BASIC = "basic"  # Expected features
    PERFORMANCE = "performance"  # Linear satisfaction
    DELIGHT = "delight"  # Unexpected features
    INDIFFERENT = "indifferent"  # No impact
    REVERSE = "reverse"  # Causes dissatisfaction


class PrioritizationEngine:
    """
    Multi-framework prioritization engine.
    
    Supports:
    - MoSCoW method
    - Kano model
    - Weighted scoring
    - AI-driven prioritization
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the prioritization engine."""
        self.settings = settings or get_settings()
        
        logger.info("PrioritizationEngine initialized")

    def moscow_prioritize(
        self,
        requirements: list[dict],
        must_have: Optional[list[str]] = None,
        should_have: Optional[list[str]] = None,
        could_have: Optional[list[str]] = None,
        wont_have: Optional[list[str]] = None,
    ) -> dict:
        """
        Prioritize requirements using MoSCoW method.
        
        Args:
            requirements: List of requirement dictionaries
            must_have: Optional list of requirement IDs that are must-have
            should_have: Optional list of requirement IDs that are should-have
            could_have: Optional list of requirement IDs that are could-have
            wont_have: Optional list of requirement IDs that are wont-have
            
        Returns:
            Prioritized requirements with MoSCoW categories
        """
        categorized = {
            PriorityCategory.MUST_HAVE: [],
            PriorityCategory.SHOULD_HAVE: [],
            PriorityCategory.COULD_HAVE: [],
            PriorityCategory.WONT_HAVE: [],
        }
        
        for req in requirements:
            req_id = req.get("id", "")
            
            if must_have and req_id in must_have:
                category = PriorityCategory.MUST_HAVE
            elif should_have and req_id in should_have:
                category = PriorityCategory.SHOULD_HAVE
            elif could_have and req_id in could_have:
                category = PriorityCategory.COULD_HAVE
            elif wont_have and req_id in wont_have:
                category = PriorityCategory.WONT_HAVE
            else:
                # Auto-categorize based on priority field
                priority = req.get("priority", "medium").lower()
                if priority == "high":
                    category = PriorityCategory.MUST_HAVE
                elif priority == "medium":
                    category = PriorityCategory.SHOULD_HAVE
                else:
                    category = PriorityCategory.COULD_HAVE
            
            categorized[category].append({**req, "moscow_category": category.value})
        
        return categorized

    def weighted_score(
        self,
        requirements: list[dict],
        weights: Optional[dict[str, float]] = None,
    ) -> list[dict]:
        """
        Prioritize using weighted scoring.
        
        Args:
            requirements: List of requirement dictionaries
            weights: Optional weights for scoring dimensions
                Default: {"business_value": 0.4, "effort": 0.3, "risk": 0.2, "dependencies": 0.1}
            
        Returns:
            Requirements sorted by weighted score (descending)
        """
        if weights is None:
            weights = {
                "business_value": 0.4,
                "effort": 0.3,
                "risk": 0.2,
                "dependencies": 0.1,
            }
        
        scored_requirements = []
        
        for req in requirements:
            # Extract scores (assumes requirements have these fields)
            business_value = req.get("business_value", 5.0)  # 1-10 scale
            effort = 10.0 - req.get("effort", 5.0)  # Invert effort (lower is better)
            risk = 10.0 - req.get("risk", 5.0)  # Invert risk (lower is better)
            dependencies = 10.0 - len(req.get("dependencies", []))  # Fewer deps is better
            
            # Normalize to 1-10 scale
            business_value = min(10, max(1, business_value))
            effort = min(10, max(1, effort))
            risk = min(10, max(1, risk))
            dependencies = min(10, max(1, dependencies))
            
            # Calculate weighted score
            weighted_score = (
                business_value * weights["business_value"]
                + effort * weights["effort"]
                + risk * weights["risk"]
                + dependencies * weights["dependencies"]
            )
            
            scored_requirements.append({
                **req,
                "weighted_score": round(weighted_score, 2),
                "scoring_breakdown": {
                    "business_value": business_value,
                    "effort": effort,
                    "risk": risk,
                    "dependencies": dependencies,
                },
            })
        
        # Sort by weighted score (descending)
        scored_requirements.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        return scored_requirements

    def kano_analyze(
        self,
        requirement: dict,
    ) -> dict:
        """
        Analyze requirement using Kano model.
        
        Args:
            requirement: Requirement dictionary
            
        Returns:
            Kano category and analysis
        """
        # Simple heuristic-based Kano analysis
        # In practice, this requires stakeholder surveys
        
        description = requirement.get("description", "").lower()
        priority = requirement.get("priority", "medium").lower()
        
        # Heuristics for Kano categories
        if priority == "high" and any(word in description for word in ["must", "shall", "required"]):
            category = KanoCategory.BASIC
        elif any(word in description for word in ["enhance", "improve", "optimize", "better"]):
            category = KanoCategory.PERFORMANCE
        elif any(word in description for word in ["innovative", "surprise", "delight", "wow"]):
            category = KanoCategory.DELIGHT
        else:
            category = KanoCategory.INDIFFERENT
        
        return {
            "requirement_id": requirement.get("id"),
            "kano_category": category.value,
            "category_description": self._get_kano_description(category),
        }

    def _get_kano_description(self, category: KanoCategory) -> str:
        """Get description for Kano category."""
        descriptions = {
            KanoCategory.BASIC: "Basic need - expected by users, causes dissatisfaction if missing",
            KanoCategory.PERFORMANCE: "Performance need - more is better, linear satisfaction",
            KanoCategory.DELIGHT: "Delight need - unexpected, causes high satisfaction",
            KanoCategory.INDIFFERENT: "Indifferent - no significant impact on satisfaction",
            KanoCategory.REVERSE: "Reverse - causes dissatisfaction",
        }
        return descriptions.get(category, "")
