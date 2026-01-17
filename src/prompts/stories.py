"""Prompt templates for user story generation."""

from typing import Optional


class UserStoryPrompts:
    """Prompt templates for generating JIRA-formatted user stories."""

    @staticmethod
    def get_story_generation_prompt(
        requirement_text: str,
        requirement_id: Optional[str] = None,
        requirement_type: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Get prompt for generating a user story from a requirement.
        
        Args:
            requirement_text: Requirement text
            requirement_id: Optional requirement ID
            requirement_type: Optional requirement type (functional/non-functional)
            context: Optional additional context
            
        Returns:
            Formatted prompt string
        """
        context_section = ""
        if context:
            context_section = f"""
Context:
{context}
"""
        
        req_id_section = ""
        if requirement_id:
            req_id_section = f"Requirement ID: {requirement_id}\n"
        
        req_type_section = ""
        if requirement_type:
            req_type_section = f"Requirement Type: {requirement_type}\n"
        
        prompt = f"""You are an expert product owner tasked with creating user stories from requirements.

{context_section}
{req_id_section}{req_type_section}Requirement:
"{requirement_text}"

Create a user story in JIRA format. The user story should include:

1. **Title/Summary**: A concise, user-focused title (max 255 characters for JIRA)
2. **Description**: User story in the format "As a [user type], I want [goal] so that [benefit]"
3. **Acceptance Criteria**: 3-7 specific, testable acceptance criteria using the format "Given [context], When [action], Then [expected result]"
4. **Story Points**: Estimate using Fibonacci scale (1, 2, 3, 5, 8, 13, 21) based on complexity
5. **Labels/Tags**: Relevant tags (e.g., "backend", "frontend", "api", "database")
6. **Priority**: Map from requirement priority (high/medium/low) to JIRA priority

Guidelines:
- Write from the user's perspective, not the system's
- Make acceptance criteria specific, measurable, and testable
- Story points should reflect effort, complexity, and uncertainty
- Keep description clear and focused on value
- Use standard JIRA terminology and formats

Return as JSON:
```json
{{
  "title": "User story title",
  "description": "As a [user type], I want [goal] so that [benefit]",
  "acceptance_criteria": [
    "Given [context], When [action], Then [expected result]",
    ...
  ],
  "story_points": 5,
  "labels": ["tag1", "tag2"],
  "priority": "High",
  "issue_type": "Story"
}}
```"""
        
        return prompt

    @staticmethod
    def get_batch_story_prompt(
        requirements: list[dict[str, str]],
        context: Optional[str] = None,
    ) -> str:
        """
        Get prompt for generating multiple user stories from requirements.
        
        Args:
            requirements: List of requirement dictionaries with 'id', 'text', 'type', 'priority'
            context: Optional additional context
            
        Returns:
            Formatted prompt string
        """
        context_section = ""
        if context:
            context_section = f"""
Context:
{context}
"""
        
        reqs_section = "\n\n".join([
            f"Requirement {i+1} (ID: {req.get('id', 'N/A')}, Type: {req.get('type', 'N/A')}, Priority: {req.get('priority', 'N/A')}):\n{req.get('text', '')}"
            for i, req in enumerate(requirements)
        ])
        
        prompt = f"""You are an expert product owner tasked with creating user stories from multiple requirements.

{context_section}
Requirements:
{reqs_section}

For each requirement, create a user story in JIRA format. Each story should include:

1. **Title/Summary**: Concise, user-focused title (max 255 characters)
2. **Description**: "As a [user type], I want [goal] so that [benefit]"
3. **Acceptance Criteria**: 3-7 specific, testable criteria using "Given/When/Then" format
4. **Story Points**: Fibonacci estimate (1, 2, 3, 5, 8, 13, 21)
5. **Labels**: Relevant tags
6. **Priority**: Mapped from requirement priority

Return as JSON array:
```json
[
  {{
    "requirement_id": "REQ-001",
    "title": "User story title",
    "description": "As a [user type], I want [goal] so that [benefit]",
    "acceptance_criteria": ["Given...", "When...", "Then..."],
    "story_points": 5,
    "labels": ["tag1", "tag2"],
    "priority": "High",
    "issue_type": "Story"
  }},
  ...
]
```"""
        
        return prompt

    @staticmethod
    def get_story_points_estimation_prompt(
        description: str,
        acceptance_criteria: list[str],
    ) -> str:
        """
        Get prompt for estimating story points.
        
        Args:
            description: User story description
            acceptance_criteria: List of acceptance criteria
            
        Returns:
            Formatted prompt string
        """
        criteria_text = "\n".join([f"- {crit}" for crit in acceptance_criteria])
        
        prompt = f"""Estimate story points for the following user story using Fibonacci scale (1, 2, 3, 5, 8, 13, 21).

Description: {description}

Acceptance Criteria:
{criteria_text}

Consider:
- Complexity: How complex is the implementation?
- Effort: How much work is required?
- Uncertainty: How much is unknown or risky?
- Dependencies: Are there external dependencies?

Return only the story point number (e.g., 5):"""
        
        return prompt
