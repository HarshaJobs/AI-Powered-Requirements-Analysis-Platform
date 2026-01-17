"""Text chunking strategies using token-based splitting."""

from typing import Optional, Any
import structlog

from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class TokenTextSplitter:
    """
    Text splitter that splits documents into chunks based on token count.
    
    Uses tiktoken for accurate token counting and RecursiveCharacterTextSplitter
    for intelligent splitting that respects sentence boundaries.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        model_name: str = "gpt-4",
        settings: Optional[Settings] = None,
    ):
        """
        Initialize the token-based text splitter.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            model_name: Model name for tiktoken encoding (default: gpt-4)
            settings: Optional settings instance
        """
        self.settings = settings or get_settings()
        self.chunk_size = chunk_size or self.settings.chunk_size
        self.chunk_overlap = chunk_overlap or self.settings.chunk_overlap
        self.model_name = model_name
        
        # Initialize tiktoken encoding
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base (used by GPT-4 and text-embedding-ada-002)
            logger.warning(
                "Model encoding not found, using cl100k_base",
                model_name=model_name,
            )
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Use RecursiveCharacterTextSplitter for intelligent splitting
        # We'll override the length function to use tokens instead of characters
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size * 4,  # Approximate character count (tokens ~= chars/4)
            chunk_overlap=self.chunk_overlap * 4,
            length_function=self._count_tokens,
            separators=[
                "\n\n",
                "\n",
                ". ",
                "! ",
                "? ",
                "; ",
                ", ",
                " ",
                "",
            ],
            keep_separator=True,
        )
        
        logger.info(
            "TokenTextSplitter initialized",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            model_name=model_name,
        )

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def split_documents(self, documents: list) -> list:
        """
        Split documents into chunks based on token count.
        
        Args:
            documents: List of Document objects to split
            
        Returns:
            List of Document objects with chunked content
        """
        all_chunks = []
        
        for doc_idx, doc in enumerate(documents):
            try:
                # Count tokens in original document
                original_tokens = self._count_tokens(doc.page_content)
                
                # If document is smaller than chunk size, keep as-is
                if original_tokens <= self.chunk_size:
                    # Add chunk metadata
                    chunk_metadata = {
                        **doc.metadata,
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "token_count": original_tokens,
                        "is_standalone": True,
                    }
                    from langchain_core.documents import Document
                    chunk = Document(
                        page_content=doc.page_content,
                        metadata=chunk_metadata,
                    )
                    all_chunks.append(chunk)
                    continue
                
                # Split the document
                # First, we'll manually split to ensure token-based boundaries
                chunks = self._split_by_tokens(doc.page_content)
                
                # Create Document objects for each chunk
                for chunk_idx, chunk_text in enumerate(chunks):
                    chunk_tokens = self._count_tokens(chunk_text)
                    
                    chunk_metadata = {
                        **doc.metadata,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                        "token_count": chunk_tokens,
                        "is_standalone": False,
                    }
                    
                    from langchain_core.documents import Document
                    chunk = Document(
                        page_content=chunk_text,
                        metadata=chunk_metadata,
                    )
                    all_chunks.append(chunk)
                
                logger.debug(
                    "Document split into chunks",
                    doc_idx=doc_idx,
                    original_tokens=original_tokens,
                    num_chunks=len(chunks),
                )
                
            except Exception as e:
                logger.error(
                    "Error splitting document",
                    doc_idx=doc_idx,
                    error=str(e),
                )
                # Keep original document if splitting fails
                all_chunks.append(doc)
        
        logger.info(
            "Documents split into chunks",
            input_documents=len(documents),
            output_chunks=len(all_chunks),
        )
        
        return all_chunks

    def _split_by_tokens(self, text: str) -> list[str]:
        """
        Split text into chunks based on token count with overlap.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Encode text to tokens
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        # If text fits in one chunk, return as-is
        if total_tokens <= self.chunk_size:
            return [text]
        
        chunks = []
        start_idx = 0
        
        while start_idx < total_tokens:
            # Calculate end index
            end_idx = min(start_idx + self.chunk_size, total_tokens)
            
            # Extract tokens for this chunk
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Clean up any incomplete words at boundaries
            if start_idx > 0:
                # Try to find a better boundary (sentence, paragraph, etc.)
                chunk_text = self._adjust_boundary(chunk_text, is_start=False)
            
            chunks.append(chunk_text)
            
            # Move start position with overlap
            start_idx = end_idx - self.chunk_overlap
            
            # Prevent infinite loop
            if start_idx >= end_idx:
                start_idx = end_idx
        
        return chunks

    def _adjust_boundary(self, text: str, is_start: bool = True) -> str:
        """
        Adjust chunk boundary to respect sentence/paragraph boundaries.
        
        Args:
            text: Text chunk to adjust
            is_start: True if this is the start of a chunk (looking for end boundary)
                      False if this is the end of a chunk (looking for start boundary)
            
        Returns:
            Adjusted text
        """
        # Simple heuristic: look for sentence endings
        # For end boundaries, try to find the last sentence ending before the token limit
        # For start boundaries, try to find the first sentence start after the overlap
        
        if is_start:
            # Look for first sentence/paragraph start
            for sep in ["\n\n", "\n", ". ", "! ", "? "]:
                idx = text.find(sep)
                if idx > 0:
                    return text[idx + len(sep):]
        else:
            # Look for last sentence/paragraph end
            for sep in [". ", "! ", "?", "\n\n", "\n"]:
                idx = text.rfind(sep)
                if idx > 0:
                    return text[:idx + len(sep)]
        
        return text
