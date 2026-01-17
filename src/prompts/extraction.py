"""Prompt templates for requirements extraction."""

from typing import Optional


class RequirementsExtractionPrompts:
    """Prompt templates for extracting requirements from transcripts and documents."""

    @staticmethod
    def get_extraction_prompt(
        transcript: str,
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Get the prompt for extracting requirements from a meeting transcript.
        
        Args:
            transcript: Meeting transcript text
            additional_context: Optional additional context (e.g., project context)
            
        Returns:
            Formatted prompt string
        """
        context_section = ""
        if additional_context:
            context_section = f"""
Additional Context:
{additional_context}
"""
        
        prompt = f"""You are an expert business analyst tasked with extracting requirements from meeting transcripts and documents.

Your task is to analyze the following meeting transcript and extract all requirements, both functional and non-functional.

{context_section}
Meeting Transcript:
---
{transcript}
---

Please extract all requirements from the transcript. For each requirement, provide:

1. **Requirement ID**: A unique identifier (e.g., REQ-001, REQ-002)
2. **Type**: Either "functional" or "non-functional"
3. **Description**: A clear, concise statement of the requirement
4. **Priority**: "high", "medium", or "low" based on stakeholder emphasis and business impact
5. **Source Quote**: The exact quote or paraphrased statement from the transcript that indicates this requirement
6. **Stakeholder**: The person or role who mentioned this requirement
7. **Needs Clarification**: Boolean indicating if the requirement is vague or needs more details

Guidelines:
- Extract distinct, specific requirements (not general discussion points)
- Functional requirements describe what the system should do (features, behaviors, actions)
- Non-functional requirements describe how the system should perform (performance, security, usability, etc.)
- Assign priority based on stakeholder emphasis, business impact, and urgency indicators
- If a requirement is ambiguous or lacks detail, mark "Needs Clarification" as true
- Group related requirements that are variations of the same need into a single requirement
- Be thorough but avoid over-extraction of casual comments or questions

Return your response as a JSON array of requirements with the following structure:
```json
[
  {{
    "id": "REQ-001",
    "type": "functional",
    "description": "Clear requirement statement",
    "priority": "high",
    "source_quote": "Exact quote or paraphrase",
    "stakeholder": "Person or role",
    "needs_clarification": false
  }}
]
```

Extract all requirements from the transcript:"""
        
        return prompt

    @staticmethod
    def get_batch_extraction_prompt(
        documents: list[str],
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Get the prompt for batch extraction from multiple documents.
        
        Args:
            documents: List of document texts
            additional_context: Optional additional context
            
        Returns:
            Formatted prompt string
        """
        context_section = ""
        if additional_context:
            context_section = f"""
Additional Context:
{additional_context}
"""
        
        docs_section = "\n\n---\n\n".join([
            f"Document {i+1}:\n{doc}"
            for i, doc in enumerate(documents)
        ])
        
        prompt = f"""You are an expert business analyst tasked with extracting requirements from multiple documents.

Your task is to analyze the following documents and extract all requirements, both functional and non-functional.

{context_section}
Documents:
---
{docs_section}
---

Please extract all requirements from all documents. For each requirement, provide:

1. **Requirement ID**: A unique identifier (e.g., REQ-001, REQ-002)
2. **Type**: Either "functional" or "non-functional"
3. **Description**: A clear, concise statement of the requirement
4. **Priority**: "high", "medium", or "low"
5. **Source Quote**: The exact quote or paraphrased statement indicating this requirement
6. **Stakeholder**: The person, role, or document section that mentioned this requirement
7. **Document Source**: Which document number this requirement came from
8. **Needs Clarification**: Boolean indicating if the requirement is vague or needs more details

Guidelines:
- Extract distinct, specific requirements from all documents
- Functional requirements describe what the system should do
- Non-functional requirements describe how the system should perform
- Assign priority based on emphasis, business impact, and urgency
- If a requirement is ambiguous, mark "Needs Clarification" as true
- Group related requirements that are variations of the same need

Return your response as a JSON array of requirements:
```json
[
  {{
    "id": "REQ-001",
    "type": "functional",
    "description": "Clear requirement statement",
    "priority": "high",
    "source_quote": "Exact quote or paraphrase",
    "stakeholder": "Person/role/document section",
    "document_source": 1,
    "needs_clarification": false
  }}
]
```

Extract all requirements from the documents:"""
        
        return prompt

    @staticmethod
    def get_categorization_prompt(
        requirement_text: str,
    ) -> str:
        """
        Get the prompt for categorizing a single requirement.
        
        Args:
            requirement_text: Requirement text to categorize
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert business analyst. Categorize the following requirement.

Requirement: "{requirement_text}"

Determine:
1. **Type**: "functional" or "non-functional"
2. **Category**: More specific category (e.g., "authentication", "performance", "data validation")
3. **Priority**: "high", "medium", or "low" (if not already specified)

Return as JSON:
```json
{{
  "type": "functional",
  "category": "authentication",
  "priority": "high"
}}
```"""
        
        return prompt
