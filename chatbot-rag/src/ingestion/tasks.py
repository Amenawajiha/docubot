"""Celery tasks for document ingestion, deletion, sync, and clearing."""
import os
import requests
from qdrant_client.http import models
from src.celery_app import celery_app
from src.ingestion.qdrant_loader import QdrantLoader
from src.utils import logger

WEBSITE_BACKEND_URL = os.getenv("WEBSITE_BACKEND_URL", "http://localhost:8001")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "local_development_internal_api_key")

def _notify_backend(job_id: str, status: str, chunks_created: int = 0, error: str = None):
    """Call back to website backend to update job status."""
    try:
        payload = {
            "job_status": status,
            "chunks_created": chunks_created,
        }
        if error:
            payload["error_message"] = error
        
        response = requests.post(
            f"{WEBSITE_BACKEND_URL}/api/internal/ingestion-jobs/{job_id}",
            json=payload,
            headers={"X-Internal-API-Key": INTERNAL_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"Notified backend: job {job_id} → {status} (HTTP {response.status_code})")
    except Exception as e:
        logger.error(f"Failed to notify backend: {e}")


@celery_app.task(bind=True, max_retries=3)
def ingest_document(self, job_id, document_id, workspace_id, chatbot_id, 
                    filename, file_type, download_url, collection_name):
    """
    Download file, process, chunk, embed, and upsert to Qdrant.
    """
    try:
        logger.info(f"Starting ingestion: job={job_id}, doc={document_id}, collection={collection_name}")
        
        # Notify backend: processing started
        _notify_backend(job_id, "processing")
        
        # Download file
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()
        file_bytes = response.content
        
        # Process with QdrantLoader (accepts dynamic collection_name)
        loader = QdrantLoader(collection_name=collection_name)
        stats = loader.process_document(file_bytes, filename)
        
        chunks_created = stats.get("chunks_created", 0)
        
        # Notify backend: completed
        _notify_backend(job_id, "completed", chunks_created=chunks_created)
        logger.info(f"Completed ingestion: job={job_id}, chunks={chunks_created}")
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        _notify_backend(job_id, "failed", error=str(e))
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def delete_document(workspace_id, chatbot_id, document_id, filename: str, collection_name: str = None):
    try:
        # Fallback if website backend didn't send collection_name
        if not collection_name:
            collection_name = f"workspace_{workspace_id}_chatbot_{chatbot_id}"

        loader = QdrantLoader(collection_name=collection_name)
        
        # Trigger the QdrantLoader method for cascade deletion of chunks
        loader.delete_document_chunks(filename)
        logger.info(f"Triggered chunk deletion for document {filename} in {collection_name}")
        
    except Exception as e:
        logger.error(f"Delete failed: {e}")


@celery_app.task
def sync_collection(workspace_id, chatbot_id, collection_name: str = None, document_ids: list = None):
    logger.info(f"Sync requested for workspace={workspace_id}, chatbot={chatbot_id}")
    return {"status": "synced"}


@celery_app.task
def clear_collection(workspace_id, chatbot_id, collection_name: str = None):
    try:
        if not collection_name:
            collection_name = f"workspace_{workspace_id}_chatbot_{chatbot_id}"
            
        loader = QdrantLoader(collection_name=collection_name)
        
        # FIX: Use underlying client to delete the collection
        loader.qdrant_db_client.client.delete_collection(collection_name=collection_name)
        logger.info(f"Cleared collection: {collection_name}")
    except Exception as e:
        logger.error(f"Clear failed: {e}")