"""VectorRetriever is a module for retrieving relevant documents from a vector database, with optional reranking."""

from typing import List

from src.models import RetrievalResult
from src.utils.config_loader import get_config

# from src.vector.chroma_db_client import ChromaDBClient
from src.vector.qdrant_db_client import QdrantDBClient
from src.vector.reranker import Reranker


class VectorRetriever:
    """VectorRetriever is a class that retrieves relevant documents from a vector database."""

    def __init__(self, embedding_manager=None, collection_name=None, top_k=None, reranker=None):
        """
        Initialize VectorRetriever.

        Args:
            embedding_manager: Shared EmbeddingManager instance for query embeddings.
                              If None, will be set later by ServiceManager.
            collection_name: Optional override for multi-tenant setup.
            top_k: Optional override for multi-tenant setup.
        """
        self.client = QdrantDBClient()
        self.collection_name = collection_name or get_config("vector.collection_name")
        self.top_k = top_k or get_config("rag.retrieval_top_k")
        self.reranker = reranker if reranker is not None else Reranker()
        self.embedding_manager = embedding_manager  # Will be set by ServiceManager

    def retrieve(self, query: str) -> List[RetrievalResult]:
        """Retrieve relevant documents from a vector database."""
        if not query:
            raise AttributeError("Query cannot be None or empty")

        # Generate query embedding using shared EmbeddingManager
        query_embedding = self.embedding_manager.embed_single_text(query)

        # Query with the embedding
        results = self.client.query_collection(
            self.collection_name, query_embedding, self.top_k
        )
        return results

    def retrieve_with_reranking(
        self, query: str, initial_k: int = 10
    ) -> List[RetrievalResult]:
        """Retrieve relevant documents from a vector database with reranking.

        This implements a two-stage retrieval approach:
        1. Fetch initial_k candidates from the vector database
        2. Rerank using the cross-encoder model
        3. Return top-k most relevant results

        Args:
            query: The search query
            initial_k: Number of initial candidates to fetch (should be > top_k)

        Returns:
            Top-k reranked results

        Raises:
            ValueError: If reranker is not configured
        """
        if not query:
            raise AttributeError("Query cannot be None or empty")

        # Generate query embedding using shared EmbeddingManager
        query_embedding = self.embedding_manager.embed_single_text(query)

        # Fetch initial candidates from vector database
        results = self.client.query_collection(
            self.collection_name, query_embedding, initial_k
        )

        if not self.reranker:
            raise ValueError("Reranker is not configured")

        # Rerank and return top-k
        reranked_results = self.reranker.rerank(query, results)

        return reranked_results
