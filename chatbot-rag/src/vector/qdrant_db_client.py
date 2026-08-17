"""Qdrant client for vector database operations."""

import os
import time
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException

from src.models import RetrievalResult
from src.utils.config_loader import get_config
from src.utils import logger


class QdrantDBClient:
    """QdrantDBClient is a client for the Qdrant vector database."""

    def __init__(self):
        self.url = os.getenv("QDRANT_HOST", get_config("vector.qdrant_url"))
        self.port = int(os.getenv("QDRANT_PORT", get_config("vector.qdrant_port")))
        self.api_key = os.getenv("QDRANT_API_KEY")

        # Timeout configuration
        self.timeout = get_config("vector.qdrant_timeout", 60)

        # Retry configuration
        self.max_retries = get_config("vector.qdrant_max_retries", 3)
        self.retry_delay = get_config("vector.qdrant_retry_delay", 1.0)

        self.client = QdrantClient(
            url=self.url,
            port=self.port,
            api_key=self.api_key,
            timeout=self.timeout,
        )

        logger.info(
            "QdrantClient initialized with timeout=%ds",
            self.timeout,
        )

    def query_collection(
        self,
        collection_name: str,
        query_embedding,
        top_k: int = 30,
    ) -> List[RetrievalResult]:
        """
        Query a collection using a pre-computed embedding.

        Args:
            collection_name: Name of the collection
            query_embedding: Pre-computed query embedding (numpy array or list)
            top_k: Number of results to return

        Returns:
            List of retrieval results
        """
        # Convert numpy array to list if needed
        if hasattr(query_embedding, "tolist"):
            query_embedding = query_embedding.tolist()

        search_results = self.client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=top_k,
            with_payload=True,
        ).points

        formatted_results = []
        for point in search_results:
            payload = point.payload or {}

            # Extract content (support both 'page_content' and 'content' keys)
            content = payload.get("page_content") or payload.get("content") or ""

            # Metadata is the rest of the payload
            metadata = payload.copy()
            if "page_content" in metadata:
                del metadata["page_content"]
            if "content" in metadata:
                del metadata["content"]

            formatted_results.append(
                RetrievalResult(
                    content=content,
                    metadata=metadata,
                    relevance_score=point.score,
                )
            )

        return formatted_results

    def upsert(self, collection_name: str, points: List[models.PointStruct]):
        """Upsert points into the collection with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                self.client.upsert(collection_name=collection_name, points=points)
                logger.info(
                    "Successfully upserted %d points to collection '%s'",
                    len(points),
                    collection_name,
                )
                return
            except ResponseHandlingException as e:
                if attempt == self.max_retries:
                    logger.error(
                        "Failed to upsert points after %d attempts: %s",
                        self.max_retries + 1,
                        str(e),
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = self.retry_delay * (2**attempt)
                logger.warning(
                    "Upsert attempt %d failed, retrying in %.1fs: %s",
                    attempt + 1,
                    delay,
                    str(e),
                )
                time.sleep(delay)

    def delete(self, collection_name: str, point_ids: List[str]):
        """Delete points from the collection."""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=point_ids),
        )

    def delete_by_filter(self, collection_name: str, key: str, value: str):
        """Delete points matching a metadata filter."""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    ]
                )
            ),
        )

    def count(self, collection_name: str) -> int:
        """Count points in the collection."""
        return self.client.count(collection_name=collection_name).count

    def ensure_collection(self, collection_name: str):
        """Ensure collection exists, create if not."""
        try:
            self.client.get_collection(collection_name)
        except Exception as e:
            logger.debug(e)
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=get_config("vector.embedding_dimension"),
                    distance=models.Distance.COSINE,
                ),
            )

        # Ensure index on document_name for filtering/deletion
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="document_name",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


if __name__ == "__main__":
    # Test connection
    from dotenv import load_dotenv

    load_dotenv()

    print("Testing Qdrant connection...")
    try:
        db = QdrantDBClient()
        collections = db.client.get_collections()
        print(f"Connected successfully. Collections: {collections}")
    except Exception as e:
        print(f"Connection failed: {e}")
