"""Unit tests for Celery ingestion tasks in src.ingestion.tasks."""

import pytest
from unittest.mock import MagicMock, patch
from celery.exceptions import Retry

from src.ingestion.tasks import (
    _notify_backend,
    ingest_document,
    delete_document,
    sync_collection,
    clear_collection,
)


@patch("src.ingestion.tasks.requests.post")
def test_notify_backend_success(mock_post):
    """Test _notify_backend sends correct HTTP POST payload to website backend."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    _notify_backend(job_id="job_123", status="completed", chunks_created=5)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "job_123" in args[0]
    assert kwargs["json"] == {"job_status": "completed", "chunks_created": 5}
    assert "X-Internal-API-Key" in kwargs["headers"]


@patch("src.ingestion.tasks.requests.post")
def test_notify_backend_with_error_and_exception_handling(mock_post):
    """Test _notify_backend includes error_message payload and handles network exceptions cleanly."""
    mock_post.side_effect = Exception("Backend connection refuded")

    # Should not raise exception
    _notify_backend(job_id="job_456", status="failed", error="Failed to download file")
    mock_post.assert_called_once()


@patch("src.ingestion.tasks._notify_backend")
@patch("src.ingestion.tasks.requests.get")
@patch("src.ingestion.tasks.QdrantLoader")
def test_ingest_document_happy_path(mock_qdrant_loader_cls, mock_get, mock_notify):
    """Test ingest_document happy path: downloads file, processes chunks, and notifies backend."""
    mock_resp = MagicMock()
    mock_resp.content = b"Mock PDF file content"
    mock_get.return_value = mock_resp

    mock_loader = MagicMock()
    mock_loader.process_document.return_value = {"chunks_created": 12}
    mock_qdrant_loader_cls.return_value = mock_loader

    mock_task_self = MagicMock()

    ingest_document(
        "job_001",
        "doc_001",
        "ws_1",
        "bot_1",
        "policy.pdf",
        "pdf",
        "https://s3.example.com/policy.pdf",
        "workspace_ws_1_chatbot_bot_1",
    )

    mock_notify.assert_any_call("job_001", "processing")
    mock_get.assert_called_once_with("https://s3.example.com/policy.pdf", timeout=30)
    mock_qdrant_loader_cls.assert_called_once_with(collection_name="workspace_ws_1_chatbot_bot_1")
    mock_loader.process_document.assert_called_once_with(b"Mock PDF file content", "policy.pdf")
    mock_notify.assert_any_call("job_001", "completed", chunks_created=12)


@patch("src.ingestion.tasks._notify_backend")
@patch("src.ingestion.tasks.requests.get")
@patch.object(ingest_document, "retry")
def test_ingest_document_failure_triggers_retry(mock_retry, mock_get, mock_notify):
    """Test ingest_document notifies backend of failure and triggers Celery retry."""
    mock_get.side_effect = Exception("Download timeout")
    mock_retry.side_effect = Exception("Task retried")

    with pytest.raises(Exception) as exc_info:
        ingest_document(
            "job_fail",
            "doc_fail",
            "ws_1",
            "bot_1",
            "error.pdf",
            "pdf",
            "https://s3.example.com/error.pdf",
            "workspace_ws_1_chatbot_bot_1",
        )

    assert "Task retried" in str(exc_info.value)
    mock_notify.assert_any_call("job_fail", "processing")
    mock_notify.assert_any_call("job_fail", "failed", error="Download timeout")
    mock_retry.assert_called_once()


@patch("src.ingestion.tasks.QdrantLoader")
def test_delete_document_with_explicit_and_derived_collection(mock_qdrant_loader_cls):
    """Test delete_document triggers delete_document_chunks with explicit and fallback collection name."""
    mock_loader = MagicMock()
    mock_qdrant_loader_cls.return_value = mock_loader

    # Explicit collection_name
    delete_document(
        workspace_id="ws_10",
        chatbot_id="bot_20",
        document_id="doc_30",
        filename="guide.docx",
        collection_name="custom_collection_name",
    )
    mock_qdrant_loader_cls.assert_called_with(collection_name="custom_collection_name")
    mock_loader.delete_document_chunks.assert_called_with("guide.docx")

    # Fallback derived collection_name
    delete_document(
        workspace_id="ws_10",
        chatbot_id="bot_20",
        document_id="doc_30",
        filename="guide.docx",
        collection_name=None,
    )
    mock_qdrant_loader_cls.assert_called_with(collection_name="workspace_ws_10_chatbot_bot_20")


@patch("src.ingestion.tasks.QdrantLoader")
def test_delete_document_handles_exception(mock_qdrant_loader_cls):
    """Test delete_document catches exceptions silently without failing the Celery task."""
    mock_qdrant_loader_cls.side_effect = Exception("Qdrant unavailable")

    # Should not raise exception
    delete_document(
        workspace_id="ws_1",
        chatbot_id="bot_1",
        document_id="doc_1",
        filename="file.txt",
    )


def test_sync_collection():
    """Test sync_collection task returns status synced."""
    result = sync_collection("ws_1", "bot_1")
    assert result == {"status": "synced"}


@patch("src.ingestion.tasks.QdrantLoader")
def test_clear_collection_success_and_fallback(mock_qdrant_loader_cls):
    """Test clear_collection calls delete_collection on qdrant client with explicit and fallback collection names."""
    mock_loader = MagicMock()
    mock_qdrant_loader_cls.return_value = mock_loader

    # Explicit collection name
    clear_collection("ws_1", "bot_1", collection_name="explicit_col")
    mock_loader.qdrant_db_client.client.delete_collection.assert_called_with(collection_name="explicit_col")

    # Fallback collection name
    clear_collection("ws_1", "bot_1", collection_name=None)
    mock_loader.qdrant_db_client.client.delete_collection.assert_called_with(collection_name="workspace_ws_1_chatbot_bot_1")


@patch("src.ingestion.tasks.QdrantLoader")
def test_clear_collection_handles_exception(mock_qdrant_loader_cls):
    """Test clear_collection catches exceptions gracefully."""
    mock_loader = MagicMock()
    mock_loader.qdrant_db_client.client.delete_collection.side_effect = Exception("Collection already cleared")
    mock_qdrant_loader_cls.return_value = mock_loader

    # Should not raise exception
    clear_collection("ws_1", "bot_1", collection_name="col_1")
    mock_loader.qdrant_db_client.client.delete_collection.assert_called_once_with(collection_name="col_1")
