"""
S3 / MinIO storage client — lazy singleton using aioboto3.

Used to:
  - Upload raw document files after the user submits them
  - Generate presigned download URLs for the chatbot-rag worker
  - Delete files when a document is removed

Storage key format:
    workspaces/{workspace_id}/chatbots/{chatbot_id}/documents/{document_id}/{filename}
"""

from __future__ import annotations

import uuid
from pathlib import Path

import aioboto3

from app.config import settings

_session: aioboto3.Session | None = None


def _get_session() -> aioboto3.Session:
    global _session
    if _session is None:
        _session = aioboto3.Session(
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
    return _session


def build_storage_key(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
) -> str:
    """Canonical S3 key for a document file."""
    safe = Path(filename).name   # strip any path traversal
    return (
        f"workspaces/{workspace_id}/chatbots/{chatbot_id}"
        f"/documents/{document_id}/{safe}"
    )


async def upload_file(
    storage_key: str,
    file_bytes: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload bytes to S3/MinIO. Returns the storage_key."""
    endpoint = settings.s3_endpoint_url or None
    async with _get_session().client(
        "s3",
        endpoint_url=endpoint,
    ) as s3:
        await s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=storage_key,
            Body=file_bytes,
            ContentType=content_type,
        )
    return storage_key


async def generate_presigned_url(
    storage_key: str, expires_in: int = 3600
) -> str:
    """
    Generate a time-limited presigned GET URL.
    Used by the chatbot-rag Celery worker to download the file for processing.
    """
    endpoint = settings.s3_endpoint_url or None
    async with _get_session().client(
        "s3",
        endpoint_url=endpoint,
    ) as s3:
        url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": storage_key},
            ExpiresIn=expires_in,
        )
    return url


async def delete_file(storage_key: str) -> None:
    """Delete a file from S3/MinIO."""
    endpoint = settings.s3_endpoint_url or None
    async with _get_session().client(
        "s3",
        endpoint_url=endpoint,
    ) as s3:
        await s3.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=storage_key,
        )