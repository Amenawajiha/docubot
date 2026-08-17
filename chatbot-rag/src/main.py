"""FastAPI application entry point."""

import os
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.chat.conversation_manager import ConversationManager
from src.routes import router
from src.service_manager import get_service_manager
from src.utils.log_helper import create_log_file, logger
from src.celery_app import celery_app
from src.ingestion import tasks
from src.utils.config_loader import get_config

async def cleanup_old_conversations_task():
    """Background task to cleanup old conversation files daily."""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute for testing
            conversation_manager = ConversationManager()
            deleted = conversation_manager.cleanup_old_conversations(days=7)
            logger.info(f"Cleaned up {deleted} old conversation files")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler to replace deprecated startup/shutdown events.

    This moves startup and shutdown logic into a single, well-supported
    lifespan handler and ensures the background cleanup task is properly
    cancelled on shutdown.
    """
    # Ensure a persistent log file is created in the running process
    create_log_file("rag")
    logger.info("Starting application - initializing services...")
    # Initialize heavy services (embedding, reranker, LLM)
    logger.info(f"Celery broker: {os.getenv('CELERY_BROKER_URL')}")
    logger.info(f"Celery worker configured and ready.")
    get_service_manager()
    logger.info("Application startup complete - ready to accept connections")

    # Start background cleanup task and keep a reference so we can cancel it
    cleanup_task = asyncio.create_task(cleanup_old_conversations_task())
    logger.info("Started background cleanup task (runs daily)")

    try:
        yield
    finally:
        logger.info("Shutting down application")
        # Cancel background task gracefully
        cleanup_task.cancel()
        try:
            await cleanup_task
        except Exception:
            pass


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Schengen Visa RAG Chatbot",
    description="RAG-based chatbot for Schengen visa information",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
from src.api.routes import api_router
app.include_router(api_router)


def start():
    """Start the FastAPI application."""
    should_reload = os.getenv("RELOAD", "false").lower() in ("true", "1")
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=should_reload, 
        log_level="info",
        reload_excludes=["*.log", "logs/*", "conversations/*"]
    )


if __name__ == "__main__":
    start()
