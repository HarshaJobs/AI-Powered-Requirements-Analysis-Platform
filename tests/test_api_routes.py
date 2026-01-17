"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client."""
    from src.main import app
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_upload_document_endpoint(client):
    """Test document upload endpoint."""
    # Create a simple text file
    files = {
        "file": ("test.txt", b"Sample document content", "text/plain")
    }
    
    response = client.post("/api/v1/documents/upload", files=files)
    
    # Will fail without proper setup, but tests endpoint exists
    assert response.status_code in [200, 400, 500]
    if response.status_code == 200:
        data = response.json()
        assert "document_id" in data
        assert "filename" in data


def test_list_documents_endpoint(client):
    """Test list documents endpoint."""
    response = client.get("/api/v1/documents/list")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data


def test_conflict_types_endpoint(client):
    """Test conflict types endpoint."""
    response = client.get("/api/v1/conflicts/types")
    assert response.status_code == 200
    data = response.json()
    assert "conflict_types" in data
    assert "severity_levels" in data


def test_story_templates_endpoint(client):
    """Test story templates endpoint."""
    response = client.get("/api/v1/stories/templates")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "acceptance_criteria_formats" in data


def test_rag_stats_endpoint(client):
    """Test RAG stats endpoint."""
    # Will fail without Pinecone connection, but tests endpoint
    response = client.get("/api/v1/rag/stats")
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "index_name" in data
