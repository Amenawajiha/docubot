"""
Celery application instance.

This module defines the Celery app used by the website backend to
dispatch ingestion tasks to the chatbot-rag worker.

The chatbot-rag service runs the actual Celery worker and registers
its own tasks. This backend only dispatches tasks by name using
send_task() — it does NOT import any chatbot-rag code directly.

Both services must share:
  - The same broker URL (RabbitMQ / Redis)
  - The same result backend (Redis)
  - The same task names (defined as constants below)
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "docubot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Don't wait for task results in request handlers — use polling instead
    task_ignore_result=False,
    result_expires=86400,       # 24 hours
)

# ── Task names (must match chatbot-rag worker registration) ───────────────────
TASK_INGEST_DOCUMENT = "src.ingestion.tasks.ingest_document"
TASK_DELETE_DOCUMENT = "src.ingestion.tasks.delete_document"
TASK_SYNC_COLLECTION = "src.ingestion.tasks.sync_collection"
TASK_CLEAR_COLLECTION = "src.ingestion.tasks.clear_collection"