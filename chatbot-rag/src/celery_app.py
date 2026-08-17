"""Celery worker configuration."""
import os
from celery import Celery

celery_app = Celery(
    "chatbot_rag",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379"),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["src.ingestion"])

if __name__ == "__main__":
    celery_app.start()