"""Document preprocessing pipeline."""

from typing import Optional
import hashlib

import structlog
from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.document_processing.loader import ConfluencePDFLoader, TextLoader
from src.document_processing.chunking import TokenTextSplitter

logger = structlog.get_logger(__name__)


class DocumentProcessingPipeline:
    """
    Complete pipeline for processing documents:
    1. Load documents (PDF or text)
    2. Preprocess content
    3. Extract metadata
    4. Chunk into token-based segments
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the processing pipeline."""
        self.settings = settings or get_settings()
        self.pdf_loader = ConfluencePDFLoader(settings=self.settings)
        self.text_loader = TextLoader(settings=self.settings)
        self.chunker = TokenTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            settings=self.settings,
        )

    def process_document(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        document_id: Optional[str] = None,
    ) -> tuple[list[Document], dict]:
        """
        Process a document through the complete pipeline.
        
        Args:
            content: Document content as bytes
            filename: Source filename
            content_type: MIME type (e.g., 'application/pdf', 'text/plain')
            document_id: Optional document ID (generated if not provided)
            
        Returns:
            Tuple of (chunked_documents, processing_metadata)
        """
        # Generate document ID if not provided
        if not document_id:
            document_id = hashlib.sha256(content).hexdigest()[:16]
        
        logger.info(
            "Processing document",
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
        )
        
        # Step 1: Load document
        try:
            if content_type == "application/pdf":
                raw_documents = self.pdf_loader.load_from_bytes(content, filename=filename)
            elif content_type == "text/plain":
                raw_documents = self.text_loader.load_from_bytes(content, filename=filename)
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
        except Exception as e:
            logger.error(
                "Error loading document",
                document_id=document_id,
                error=str(e),
            )
            raise
        
        # Step 2: Preprocess and enrich metadata
        preprocessed_docs = self._preprocess_documents(raw_documents, document_id, filename)
        
        # Step 3: Chunk documents
        chunked_documents = self.chunker.split_documents(preprocessed_docs)
        
        # Step 4: Finalize metadata
        chunked_documents = self._finalize_chunk_metadata(chunked_documents, document_id)
        
        # Compile processing metadata
        processing_metadata = {
            "document_id": document_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content),
            "original_documents": len(raw_documents),
            "total_chunks": len(chunked_documents),
            "chunk_size_tokens": self.settings.chunk_size,
            "chunk_overlap_tokens": self.settings.chunk_overlap,
        }
        
        logger.info(
            "Document processed successfully",
            document_id=document_id,
            total_chunks=len(chunked_documents),
        )
        
        return chunked_documents, processing_metadata

    def _preprocess_documents(
        self,
        documents: list[Document],
        document_id: str,
        filename: str,
    ) -> list[Document]:
        """
        Preprocess documents: clean text, extract metadata.
        
        Args:
            documents: Raw documents from loader
            document_id: Document ID
            filename: Source filename
            
        Returns:
            Preprocessed documents with enriched metadata
        """
        preprocessed = []
        
        for doc in documents:
            # Clean page content
            cleaned_content = self._clean_text(doc.page_content)
            
            # Enrich metadata
            enriched_metadata = {
                **doc.metadata,
                "document_id": document_id,
                "filename": filename,
            }
            
            # Add text statistics
            enriched_metadata.update(self._extract_text_statistics(cleaned_content))
            
            # Create new document with cleaned content
            preprocessed_doc = Document(
                page_content=cleaned_content,
                metadata=enriched_metadata,
            )
            preprocessed.append(preprocessed_doc)
        
        return preprocessed

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        import re
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        
        # Remove empty lines at start/end
        text = text.strip()
        
        return text

    def _extract_text_statistics(self, text: str) -> dict:
        """
        Extract statistics about the text content.
        
        Args:
            text: Text content
            
        Returns:
            Dictionary of statistics
        """
        lines = text.split("\n")
        words = text.split()
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        
        return {
            "char_count": len(text),
            "word_count": len(words),
            "line_count": len(lines),
            "sentence_count": len([s for s in sentences if s.strip()]),
        }

    def _finalize_chunk_metadata(
        self,
        chunks: list[Document],
        document_id: str,
    ) -> list[Document]:
        """
        Finalize metadata for all chunks.
        
        Args:
            chunks: Chunked documents
            document_id: Document ID
            
        Returns:
            Documents with finalized metadata
        """
        finalized = []
        
        for chunk in chunks:
            # Ensure document_id is set
            final_metadata = {
                **chunk.metadata,
                "document_id": document_id,
            }
            
            # Add global chunk identifier
            chunk_idx = chunk.metadata.get("chunk_index", 0)
            final_metadata["chunk_id"] = f"{document_id}_chunk_{chunk_idx}"
            
            finalized_chunk = Document(
                page_content=chunk.page_content,
                metadata=final_metadata,
            )
            finalized.append(finalized_chunk)
        
        return finalized
