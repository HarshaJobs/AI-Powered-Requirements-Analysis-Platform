"""Prompt templates for conflict detection between requirements."""

from typing import Optional


class ConflictDetectionPrompts:
    """Prompt templates for detecting conflicts between requirements."""

    @staticmethod
    def get_pairwise_conflict_prompt(
        requirement1: str,
        requirement2: str,
        req1_id: Optional[str] = None,
        req2_id: Optional[str] = None,
    ) -> str:
        """
        Get prompt for detecting conflict between two requirements.
        
        Args:
            requirement1: First requirement text
            requirement2: Second requirement text
            req1_id: Optional ID for first requirement
            req2_id: Optional ID for second requirement
            
        Returns:
            Formatted prompt string
        """
        id_section = ""
        if req1_id or req2_id:
            id_section = f"Requirement 1 ID: {req1_id or 'N/A'}\nRequirement 2 ID: {req2_id or 'N/A'}\n\n"
        
        prompt = f"""You are an expert business analyst tasked with detecting conflicts between requirements.

{id_section}Requirement 1:
"{requirement1}"

Requirement 2:
"{requirement2}"

Analyze these two requirements for conflicts. A conflict can be:

1. **Logical Contradiction**: Requirements that cannot both be true simultaneously
2. **Resource Conflict**: Competing resource requirements (time, budget, personnel)
3. **Temporal Conflict**: Conflicting time constraints or sequence dependencies
4. **Functional Overlap**: Duplicate or overlapping functionality that causes ambiguity
5. **Design Conflict**: Conflicting architectural or design decisions

Determine:
1. **Has Conflict**: Boolean - do these requirements conflict?
2. **Conflict Type**: Type of conflict (logical, resource, temporal, overlap, design, or none)
3. **Severity**: "high", "medium", or "low"
4. **Description**: Detailed explanation of the conflict
5. **Recommendation**: Suggested resolution approach

Return as JSON:
```json
{{
  "has_conflict": true,
  "conflict_type": "logical",
  "severity": "high",
  "description": "Detailed explanation of the conflict",
  "recommendation": "Suggested resolution"
}}
```"""
        
        return prompt

    @staticmethod
    def get_batch_conflict_prompt(
        requirements: list[dict[str, str]],
    ) -> str:
        """
        Get prompt for detecting conflicts across multiple requirements.
        
        Args:
            requirements: List of requirement dicts with 'id' and 'text'
            
        Returns:
            Formatted prompt string
        """
        reqs_section = "\n\n".join([
            f"Requirement {i+1} (ID: {req.get('id', 'N/A')}):\n{req.get('text', '')}"
            for i, req in enumerate(requirements)
        ])
        
        prompt = f"""You are an expert business analyst tasked with detecting conflicts across multiple requirements.

Requirements:
{reqs_section}

Analyze all pairs of requirements for conflicts. Types of conflicts include:

1. **Logical Contradiction**: Cannot both be true
2. **Resource Conflict**: Competing resources
3. **Temporal Conflict**: Conflicting time constraints
4. **Functional Overlap**: Duplicate functionality
5. **Design Conflict**: Conflicting design decisions

For each conflicting pair, provide:

1. **Requirement 1 ID**: First requirement ID
2. **Requirement 2 ID**: Second requirement ID
3. **Conflict Type**: Type of conflict
4. **Severity**: "high", "medium", or "low"
5. **Description**: Explanation of conflict
6. **Recommendation**: Resolution approach

Return as JSON array of conflicts:
```json
[
  {{
    "requirement_1_id": "REQ-001",
    "requirement_2_id": "REQ-002",
    "conflict_type": "logical",
    "severity": "high",
    "description": "Detailed explanation",
    "recommendation": "Suggested resolution"
  }},
  ...
]
```

If no conflicts are found, return an empty array: []"""
        
        return prompt

    @staticmethod
    def get_severity_classification_prompt(
        conflict_description: str,
        conflict_type: str,
    ) -> str:
        """
        Get prompt for classifying conflict severity.
        
        Args:
            conflict_description: Description of the conflict
            conflict_type: Type of conflict
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Classify the severity of the following requirement conflict.

Conflict Type: {conflict_type}

Description: {conflict_description}

Severity Guidelines:
- **High**: Blocks implementation, causes system failure, major business impact
- **Medium**: Causes issues but workarounds exist, moderate business impact
- **Low**: Minor inconsistency, can be resolved easily, minimal impact

Consider:
- Impact on system functionality
- Impact on business objectives
- Difficulty of resolution
- Risk if left unresolved

Return only the severity level ("high", "medium", or "low"):"""
        
        return prompt
