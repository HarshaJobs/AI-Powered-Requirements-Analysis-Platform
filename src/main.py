"""FastAPI application entry point."""

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.api.routes import documents, extraction, stories, conflicts, rag

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    settings = get_settings()
    logger.info(
        "Starting Requirements Analysis Platform",
        environment=settings.app_env,
        debug=settings.app_debug,
    )
    
    # Startup: Initialize connections, load models, etc.
    # TODO: Initialize Pinecone connection
    # TODO: Warm up LLM connection
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Shutting down Requirements Analysis Platform")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI-Powered Requirements Analysis Platform",
        description=(
            "GenAI platform for automated requirements extraction, "
            "RAG-enhanced BRD querying, user story generation, and conflict detection."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware for development
    if settings.is_development:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint for Cloud Run."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.app_env,
        }

    # Register API routes
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
    app.include_router(extraction.router, prefix="/api/v1/extract", tags=["Extraction"])
    app.include_router(stories.router, prefix="/api/v1/stories", tags=["User Stories"])
    app.include_router(conflicts.router, prefix="/api/v1/conflicts", tags=["Conflicts"])
    app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG"])

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
