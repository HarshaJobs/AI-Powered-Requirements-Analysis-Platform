"""Document loaders for PDF and text files."""

import io
from typing import Optional
from pathlib import Path

import structlog
from langchain_community.document_loaders import PyPDFLoader
from pypdf import PdfReader

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class ConfluencePDFLoader:
    """Loader for Confluence PDF exports with enhanced metadata extraction."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the loader with settings."""
        self.settings = settings or get_settings()

    def load_from_bytes(self, content: bytes, filename: Optional[str] = None) -> list:
        """
        Load a PDF document from bytes.
        
        Args:
            content: PDF file content as bytes
            filename: Optional filename for metadata
            
        Returns:
            List of Document objects with page content and metadata
        """
        try:
            # Use LangChain's PyPDFLoader with BytesIO
            pdf_file = io.BytesIO(content)
            
            # Create a temporary file-like object for PyPDFLoader
            # PyPDFLoader expects a file path, so we'll use PyPDF directly
            reader = PdfReader(pdf_file)
            
            documents = []
            total_pages = len(reader.pages)
            
            logger.info(
                "Loading PDF document",
                filename=filename,
                pages=total_pages,
            )
            
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    
                    if not text.strip():
                        logger.warning(
                            "Empty page detected",
                            filename=filename,
                            page=page_num,
                        )
                        continue
                    
                    # Extract metadata
                    metadata = self._extract_metadata(
                        reader,
                        page_num,
                        total_pages,
                        filename or "unknown.pdf",
                    )
                    
                    # Create document object compatible with LangChain
                    from langchain_core.documents import Document
                    doc = Document(
                        page_content=text,
                        metadata=metadata,
                    )
                    documents.append(doc)
                    
                except Exception as e:
                    logger.error(
                        "Error extracting page",
                        filename=filename,
                        page=page_num,
                        error=str(e),
                    )
                    continue
            
            logger.info(
                "PDF loaded successfully",
                filename=filename,
                total_documents=len(documents),
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Error loading PDF",
                filename=filename,
                error=str(e),
            )
            raise ValueError(f"Failed to load PDF: {str(e)}") from e

    def load_from_path(self, file_path: Path | str) -> list:
        """
        Load a PDF document from file path.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        with open(file_path, "rb") as f:
            content = f.read()
        
        return self.load_from_bytes(content, filename=file_path.name)

    def _extract_metadata(
        self,
        reader: PdfReader,
        page_num: int,
        total_pages: int,
        filename: str,
    ) -> dict:
        """
        Extract metadata from PDF.
        
        Args:
            reader: PdfReader instance
            page_num: Current page number (1-indexed)
            total_pages: Total number of pages
            filename: Source filename
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            "source": filename,
            "page": page_num,
            "total_pages": total_pages,
            "document_type": "pdf",
        }
        
        # Try to extract PDF metadata
        try:
            pdf_metadata = reader.metadata
            if pdf_metadata:
                if pdf_metadata.title:
                    metadata["title"] = str(pdf_metadata.title)
                if pdf_metadata.author:
                    metadata["author"] = str(pdf_metadata.author)
                if pdf_metadata.creator:
                    metadata["creator"] = str(pdf_metadata.creator)
                if pdf_metadata.creation_date:
                    metadata["creation_date"] = str(pdf_metadata.creation_date)
                if pdf_metadata.modification_date:
                    metadata["modification_date"] = str(pdf_metadata.modification_date)
        except Exception as e:
            logger.debug(
                "Could not extract PDF metadata",
                error=str(e),
            )
        
        # Detect Confluence export patterns
        try:
            first_page = reader.pages[0]
            first_page_text = first_page.extract_text()
            
            # Check for Confluence indicators
            if "Confluence" in first_page_text or "atlassian" in first_page_text.lower():
                metadata["source_type"] = "confluence_export"
            else:
                metadata["source_type"] = "general_pdf"
                
        except Exception:
            metadata["source_type"] = "general_pdf"
        
        return metadata


class TextLoader:
    """Loader for plain text files (e.g., meeting transcripts)."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the loader with settings."""
        self.settings = settings or get_settings()

    def load_from_bytes(
        self,
        content: bytes,
        filename: Optional[str] = None,
        encoding: str = "utf-8",
    ) -> list:
        """
        Load a text document from bytes.
        
        Args:
            content: Text file content as bytes
            filename: Optional filename for metadata
            encoding: Text encoding (default: utf-8)
            
        Returns:
            List of Document objects
        """
        try:
            text = content.decode(encoding)
            
            logger.info(
                "Loading text document",
                filename=filename,
                size_chars=len(text),
            )
            
            from langchain_core.documents import Document
            
            metadata = {
                "source": filename or "unknown.txt",
                "document_type": "text",
                "source_type": "meeting_transcript" if self._is_transcript(text) else "general_text",
            }
            
            doc = Document(
                page_content=text,
                metadata=metadata,
            )
            
            return [doc]
            
        except UnicodeDecodeError as e:
            logger.error(
                "Encoding error loading text",
                filename=filename,
                encoding=encoding,
                error=str(e),
            )
            raise ValueError(f"Failed to decode text with encoding {encoding}: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Error loading text",
                filename=filename,
                error=str(e),
            )
            raise ValueError(f"Failed to load text: {str(e)}") from e

    def load_from_path(
        self,
        file_path: Path | str,
        encoding: str = "utf-8",
    ) -> list:
        """
        Load a text document from file path.
        
        Args:
            file_path: Path to the text file
            encoding: Text encoding (default: utf-8)
            
        Returns:
            List of Document objects
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")
        
        with open(file_path, "rb") as f:
            content = f.read()
        
        return self.load_from_bytes(content, filename=file_path.name, encoding=encoding)

    def _is_transcript(self, text: str) -> bool:
        """
        Heuristic to detect if text is a meeting transcript.
        
        Args:
            text: Text content to analyze
            
        Returns:
            True if text appears to be a transcript
        """
        text_lower = text.lower()
        
        # Common transcript patterns
        transcript_indicators = [
            "meeting notes",
            "meeting transcript",
            "attendees:",
            "date:",
            "participants:",
            "discussion:",
            "agenda:",
            "minutes",
        ]
        
        # Check if multiple indicators are present
        matches = sum(1 for indicator in transcript_indicators if indicator in text_lower)
        
        # Check for speaker patterns (e.g., "John:", "Sarah:")
        import re
        speaker_pattern = r"^\s*\w+:\s*"
        speaker_matches = len(re.findall(speaker_pattern, text, re.MULTILINE))
        
        return matches >= 2 or speaker_matches >= 3
