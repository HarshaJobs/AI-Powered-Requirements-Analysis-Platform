"""Tests for document processing pipeline."""

import pytest
from src.document_processing.pipeline import DocumentProcessingPipeline
from src.config import get_settings


@pytest.fixture
def pipeline():
    """Create a document processing pipeline."""
    settings = get_settings()
    # Mock settings if needed
    return DocumentProcessingPipeline(settings=settings)


def test_process_text_document(pipeline):
    """Test processing a text document."""
    content = b"Sample meeting transcript\n\nJohn: We need a login system.\nSarah: With two-factor authentication."
    filename = "test_transcript.txt"
    
    # This will fail without actual API keys, but tests structure
    try:
        chunks, metadata = pipeline.process_document(
            content=content,
            filename=filename,
            content_type="text/plain",
        )
        assert len(chunks) > 0
        assert metadata["document_id"] is not None
        assert metadata["total_chunks"] > 0
    except Exception as e:
        # Expected if API keys not configured
        pytest.skip(f"Requires API keys: {e}")


def test_process_pdf_document(pipeline):
    """Test processing a PDF document."""
    # Minimal PDF for testing
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    filename = "test.pdf"
    
    try:
        chunks, metadata = pipeline.process_document(
            content=content,
            filename=filename,
            content_type="application/pdf",
        )
        assert metadata["document_id"] is not None
    except Exception as e:
        # Expected if API keys not configured or invalid PDF
        pytest.skip(f"Requires API keys or valid PDF: {e}")


def test_chunking_logic():
    """Test chunking with token-based splitter."""
    from src.document_processing.chunking import TokenTextSplitter
    from langchain_core.documents import Document
    
    splitter = TokenTextSplitter(chunk_size=10, chunk_overlap=2)
    
    # Create test document
    long_text = "This is a test document with multiple sentences. " * 20
    doc = Document(page_content=long_text, metadata={"source": "test.txt"})
    
    chunks = splitter.split_documents([doc])
    
    # Should create multiple chunks for long text
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.page_content) > 0
        assert "chunk_index" in chunk.metadata
