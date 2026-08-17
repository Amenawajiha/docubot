"""
Thin wrapper around QdrantLoader for collection management.
Used by Celery tasks dispatched from website backend.
"""

from src.ingestion.qdrant_loader import QdrantLoader


class QdrantCollectionManager:
    """Facade for collection operations."""
    
    _loader: QdrantLoader = None
    
    COLLECTION_PATTERN = "workspace_{workspace_id}_chatbot_{chatbot_id}"
    
    @classmethod
    def collection_name(cls, workspace_id: str, chatbot_id: str) -> str:
        return cls.COLLECTION_PATTERN.format(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
        )
    
    @classmethod
    def _get_loader(cls) -> QdrantLoader:
        if cls._loader is None:
            cls._loader = QdrantLoader()
        return cls._loader
    
    @classmethod
    def ensure_collection(
        cls,
        workspace_id: str,
        chatbot_id: str,
    ) -> str:
        """
        Ensure collection exists using deterministic naming.
        """
        name = cls.collection_name(workspace_id, chatbot_id)
        from src.vector.qdrant_db_client import QdrantDBClient
        QdrantDBClient().ensure_collection(name)
        return name
    
    @classmethod
    def delete_points_for_document(
        cls,
        collection_name: str,
        document_id: str,
    ) -> None:
        """Delete all vectors for a document."""
        loader = cls._get_loader()
        loader.delete_document_chunks(str(document_id))
    
    @classmethod
    def delete_collection(cls, collection_name: str) -> None:
        """Delete entire collection (destructive)."""
        loader = cls._get_loader()
        try:
            loader.qdrant_db_client.client.delete_collection(collection_name)
        except Exception:
            pass  # Already deleted