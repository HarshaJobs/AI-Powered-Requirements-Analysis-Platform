"""RAG (Retrieval-Augmented Generation) pipeline."""

from typing import Optional, Any

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.config import Settings, get_settings
from src.vectorstore.pinecone_store import PineconeVectorStoreManager

logger = structlog.get_logger(__name__)


class RAGPipeline:
    """
    RAG pipeline that combines retrieval from Pinecone with LLM generation.
    
    Components:
    1. Query processing
    2. Vector retrieval from Pinecone
    3. Context assembly
    4. LLM generation with retrieved context
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the RAG pipeline."""
        self.settings = settings or get_settings()
        self.vector_store = PineconeVectorStoreManager(settings=self.settings)
        self.llm = ChatOpenAI(
            model_name=self.settings.openai_model,
            temperature=0.0,  # Deterministic responses
            openai_api_key=self.settings.openai_api_key,
        )
        
        # Create prompt template - will be constructed dynamically with context
        self.system_prompt_template = self._get_system_prompt()
        
        # Create RAG chain
        self.rag_chain = self._create_rag_chain()
        
        logger.info(
            "RAGPipeline initialized",
            model=self.settings.openai_model,
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for RAG queries."""
        return """You are an AI assistant that helps answer questions about business requirements documents (BRDs).

You have access to retrieved context from BRD documents. Use this context to answer questions accurately and comprehensively.

Guidelines:
- Base your answers strictly on the provided context
- If the context doesn't contain enough information, say so
- Be concise but thorough
- If asked about requirements, provide specific details from the context
- Cite sources when referencing specific requirements or sections

Context from BRD documents:
{context}

Answer the question based on the context above:"""

    def _create_rag_chain(self) -> Any:
        """Create the RAG chain that combines retrieval and generation."""
        def format_docs(docs):
            """Format retrieved documents for context."""
            return "\n\n".join([
                f"Document {i+1} (Source: {doc.metadata.get('source', 'unknown')}, "
                f"Page: {doc.metadata.get('page', 'N/A')}):\n{doc.page_content}"
                for i, doc in enumerate(docs)
            ])

        def retrieve_context(question: str) -> str:
            """Retrieve relevant context for the question."""
            docs = self.vector_store.similarity_search(
                query=question,
                k=self.settings.rag_top_k,
                score_threshold=self.settings.rag_score_threshold,
            )
            return format_docs(docs)

        # Create chain
        chain = (
            {
                "context": lambda x: retrieve_context(x["question"]),
                "question": RunnablePassthrough(),
            }
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )
        
        return chain

    def query(
        self,
        question: str,
        k: Optional[int] = None,
        filter: Optional[dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Query the RAG system with a question.
        
        Args:
            question: User's question
            k: Optional number of documents to retrieve (overrides settings)
            filter: Optional metadata filter for retrieval
            namespace: Optional Pinecone namespace
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        try:
            logger.info(
                "RAG query received",
                question_length=len(question),
                k=k or self.settings.rag_top_k,
            )
            
            # Use k from parameter or settings default
            search_k = k if k is not None else self.settings.rag_top_k
            
            try:
                # Retrieve context
                docs = self.vector_store.similarity_search_with_scores(
                    query=question,
                    k=search_k,
                    filter=filter,
                    namespace=namespace,
                )
                
                # Format context
                context = "\n\n".join([
                    f"Document {i+1} (Source: {doc.metadata.get('source', 'unknown')}, "
                    f"Page: {doc.metadata.get('page', 'N/A')}, "
                    f"Score: {score:.3f}):\n{doc.page_content}"
                    for i, (doc, score) in enumerate(docs)
                ])
                
                # Generate answer using LLM
                # Create prompt with context and question
                full_system_prompt = self.system_prompt_template.format(context=context)
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", full_system_prompt),
                    ("human", question),
                ])
                prompt = prompt_template.format_messages()
                
                response = self.llm.invoke(prompt)
                answer = response.content if hasattr(response, 'content') else str(response)
                
                # Extract sources
                sources = [
                    {
                        "source": doc.metadata.get("source", "unknown"),
                        "page": doc.metadata.get("page"),
                        "chunk_index": doc.metadata.get("chunk_index"),
                        "score": float(score),
                    }
                    for doc, score in docs
                ]
                
                result = {
                    "answer": answer,
                    "sources": sources,
                    "num_sources": len(sources),
                    "question": question,
                }
                
                logger.info(
                    "RAG query completed",
                    question_length=len(question),
                    answer_length=len(answer),
                    num_sources=len(sources),
                )
                
                return result
                
            finally:
                pass
                    
        except Exception as e:
            logger.error(
                "Error processing RAG query",
                error=str(e),
                question_length=len(question),
            )
            raise ValueError(f"Failed to process RAG query: {str(e)}") from e

    def find_similar_requirements(
        self,
        requirement_text: str,
        k: int = 5,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Find similar requirements in the knowledge base.
        
        Args:
            requirement_text: Requirement text to find similarities for
            k: Number of similar requirements to return
            filter: Optional metadata filter
            
        Returns:
            List of similar requirements with metadata
        """
        try:
            docs = self.vector_store.similarity_search_with_scores(
                query=requirement_text,
                k=k,
                filter=filter,
            )
            
            similar_requirements = [
                {
                    "text": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page"),
                    "document_id": doc.metadata.get("document_id"),
                    "similarity_score": float(score),
                    "metadata": doc.metadata,
                }
                for doc, score in docs
            ]
            
            logger.info(
                "Similar requirements found",
                num_results=len(similar_requirements),
            )
            
            return similar_requirements
            
        except Exception as e:
            logger.error(
                "Error finding similar requirements",
                error=str(e),
            )
            raise ValueError(f"Failed to find similar requirements: {str(e)}") from e
