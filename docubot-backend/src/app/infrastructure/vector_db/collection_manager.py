"""
QdrantCollectionManager — per-chatbot collection lifecycle.

Naming convention: workspace_{workspace_id}_chatbot_{chatbot_id}
All UUIDs have hyphens stripped to keep names under the 255-char limit
and compatible with Qdrant's allowed character set.

Vector dimensions match the chatbot-rag embedding model:
    intfloat/e5-base-v2 → 768 dimensions
"""

from __future__ import annotations

import uuid

from qdrant_client.models import Distance, VectorParams

from app.infrastructure.vector_db.qdrant_client import get_qdrant_client

# Must match the SentenceTransformer model used in chatbot-rag
_VECTOR_DIM = 768
_DISTANCE    = Distance.COSINE


def collection_name(workspace_id: uuid.UUID, chatbot_id: uuid.UUID) -> str:
    """Return the canonical Qdrant collection name for a chatbot."""
    return f"workspace_{workspace_id}_chatbot_{chatbot_id}"


async def ensure_collection(workspace_id: uuid.UUID, chatbot_id: uuid.UUID) -> str:
    """
    Create the Qdrant collection if it does not exist.
    Returns the collection name (idempotent — safe to call on every upload).
    """
    name   = collection_name(workspace_id, chatbot_id)
    client = get_qdrant_client()

    existing = await client.get_collections()
    names    = {c.name for c in existing.collections}

    if name not in names:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=_VECTOR_DIM, distance=_DISTANCE),
        )

    return name


async def delete_collection(workspace_id: uuid.UUID, chatbot_id: uuid.UUID) -> bool:
    """
    Delete the Qdrant collection for a chatbot.
    Returns True if deleted, False if it didn't exist.
    """
    name   = collection_name(workspace_id, chatbot_id)
    client = get_qdrant_client()

    existing = await client.get_collections()
    names    = {c.name for c in existing.collections}

    if name in names:
        await client.delete_collection(collection_name=name)
        return True
    return False


async def delete_points_for_document(
    workspace_id: uuid.UUID,
    chatbot_id: uuid.UUID,
    qdrant_point_ids: list[uuid.UUID],
) -> int:
    """
    Delete specific points (chunks) from the collection.
    Returns the number of points deleted.
    """
    if not qdrant_point_ids:
        return 0

    name   = collection_name(workspace_id, chatbot_id)
    client = get_qdrant_client()

    from qdrant_client.models import PointIdsList
    await client.delete(
        collection_name=name,
        points_selector=PointIdsList(
            points=[str(pid) for pid in qdrant_point_ids]
        ),
    )
    return len(qdrant_point_ids)


async def collection_info(
    workspace_id: uuid.UUID, chatbot_id: uuid.UUID
) -> dict | None:
    """
    Return basic stats about the collection.
    Returns None if the collection does not exist.
    """
    name   = collection_name(workspace_id, chatbot_id)
    client = get_qdrant_client()
    try:
        info = await client.get_collection(collection_name=name)
        vectors_count = getattr(info, "vectors_count", None) or 0
        points_count  = getattr(info, "points_count",  None) or 0
        return {
            "vectors_count": vectors_count,
            "points_count":  points_count,
            "status":        str(info.status),
        }
    except Exception:
        return None