"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    # Import here to avoid issues with environment variables
    from src.main import app
    
    return TestClient(app)


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript for testing."""
    return """
    Meeting Notes - Requirements Discussion
    Date: 2024-01-15
    Attendees: John (PM), Sarah (BA), Mike (Dev Lead)
    
    John: We need the system to allow users to upload PDF documents.
    Sarah: The upload should support files up to 50MB.
    Mike: We should validate the file type before processing.
    John: Also, users must be able to search through uploaded documents.
    Sarah: The search should return relevant snippets, not just file names.
    Mike: We need to consider rate limiting for the API.
    John: Good point. Let's set a limit of 100 requests per minute per user.
    Sarah: The system should also track which documents each user has accessed.
    """


@pytest.fixture
def sample_requirement():
    """Sample requirement for testing."""
    return {
        "id": "REQ-001",
        "type": "functional",
        "description": "The system shall allow users to upload PDF documents up to 50MB",
        "priority": "high",
        "source_quote": "We need the system to allow users to upload PDF documents",
        "stakeholder": "John (PM)",
        "needs_clarification": False,
    }


@pytest.fixture
def sample_pdf_content():
    """Sample PDF file content for testing."""
    # Minimal PDF content for testing
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
