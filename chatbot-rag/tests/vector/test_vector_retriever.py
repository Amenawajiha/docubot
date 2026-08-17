import unittest
from unittest.mock import MagicMock, patch
from src.vector.vector_retriever import VectorRetriever
from src.models import RetrievalResult

class TestVectorRetriever(unittest.TestCase):
    """
    Unit tests for the VectorRetriever class.
    """

    def setUp(self):
        """
        Set up a mock environment for VectorRetriever.
        """
        self.mock_embedding_manager = MagicMock()
        self.mock_client = MagicMock()
        self.mock_reranker = MagicMock()

        # Patch the QdrantDBClient and Reranker
        patcher_client = patch("src.vector.vector_retriever.QdrantDBClient", return_value=self.mock_client)
        patcher_reranker = patch("src.vector.vector_retriever.Reranker", return_value=self.mock_reranker)

        self.addCleanup(patcher_client.stop)
        self.addCleanup(patcher_reranker.stop)

        patcher_client.start()
        patcher_reranker.start()

        self.vector_retriever = VectorRetriever(embedding_manager=self.mock_embedding_manager)

    def test_retrieve_happy_path(self):
        """
        Test the retrieve method with valid inputs.
        """
        # Mock embedding and client behavior
        self.mock_embedding_manager.embed_single_text.return_value = [0.1, 0.2, 0.3]
        self.mock_client.query_collection.return_value = [
            RetrievalResult(
                id="1",
                score=0.9,
                payload={},
                content="Test content",
                metadata={"key": "value"},
                relevance_score=0.95,
            )
        ]

        # Call the method
        results = self.vector_retriever.retrieve("test query")

        # Assertions
        self.mock_embedding_manager.embed_single_text.assert_called_once_with("test query")
        self.mock_client.query_collection.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], RetrievalResult)

    def test_retrieve_with_reranking_happy_path(self):
        """
        Test the retrieve_with_reranking method with valid inputs.
        """
        # Mock embedding, client, and reranker behavior
        self.mock_embedding_manager.embed_single_text.return_value = [0.1, 0.2, 0.3]
        self.mock_client.query_collection.return_value = [
            RetrievalResult(
                id="1",
                score=0.9,
                payload={},
                content="Test content",
                metadata={"key": "value"},
                relevance_score=0.95,
            )
        ]
        self.mock_reranker.rerank.return_value = [
            RetrievalResult(
                id="1",
                score=0.95,
                payload={},
                content="Test content",
                metadata={"key": "value"},
                relevance_score=0.98,
            )
        ]

        # Call the method
        results = self.vector_retriever.retrieve_with_reranking("test query", initial_k=5)

        # Assertions
        self.mock_embedding_manager.embed_single_text.assert_called_once_with("test query")
        self.mock_client.query_collection.assert_called_once()
        self.mock_reranker.rerank.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], RetrievalResult)

    def test_retrieve_invalid_query(self):
        """
        Test the retrieve method with an invalid query (None).
        """
        with self.assertRaises(AttributeError):
            self.vector_retriever.retrieve(None)

    def test_retrieve_with_reranking_invalid_query(self):
        """
        Test the retrieve_with_reranking method with an invalid query (None).
        """
        with self.assertRaises(AttributeError):
            self.vector_retriever.retrieve_with_reranking(None)

    def test_retrieve_with_empty_results(self):
        """
        Test the retrieve method when the database returns no results.
        """
        # Mock embedding and client behavior
        self.mock_embedding_manager.embed_single_text.return_value = [0.1, 0.2, 0.3]
        self.mock_client.query_collection.return_value = []

        # Call the method
        results = self.vector_retriever.retrieve("test query")

        # Assertions
        self.assertEqual(len(results), 0)

    def test_retrieve_with_reranking_empty_results(self):
        """
        Test the retrieve_with_reranking method when the database returns no results.
        """
        # Mock embedding, client, and reranker behavior
        self.mock_embedding_manager.embed_single_text.return_value = [0.1, 0.2, 0.3]
        self.mock_client.query_collection.return_value = []
        self.mock_reranker.rerank.return_value = []

        # Call the method
        results = self.vector_retriever.retrieve_with_reranking("test query", initial_k=5)

        # Assertions
        self.assertEqual(len(results), 0)

    def test_retrieve_with_reranking_reranker_not_configured(self):
        """
        Test the retrieve_with_reranking method when the reranker is not configured.
        """
        # Mock embedding and client behavior
        self.mock_embedding_manager.embed_single_text.return_value = [0.1, 0.2, 0.3]
        self.mock_client.query_collection.return_value = [
            RetrievalResult(
                id="1",
                score=0.9,
                payload={},
                content="Test content",
                metadata={"key": "value"},
                relevance_score=0.95,
            )
        ]

        # Remove the reranker
        self.vector_retriever.reranker = None

        # Call the method and assert exception
        with self.assertRaises(ValueError):
            self.vector_retriever.retrieve_with_reranking("test query", initial_k=5)

if __name__ == "__main__":
    unittest.main()
