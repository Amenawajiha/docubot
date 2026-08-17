import unittest
from unittest.mock import MagicMock, patch

from src.vector.reranker import Reranker
from src.models import RetrievalResult


class TestReranker(unittest.TestCase):

    @patch("src.vector.reranker.get_config")
    @patch("src.vector.reranker.CrossEncoder")
    def setUp(self, mock_cross_encoder, mock_get_config):
        mock_get_config.side_effect = lambda key: {
            "vector.reranker_model_name": "test-model",
            "rag.rerank_top_k": 2,
        }[key]

        self.mock_model = MagicMock()
        mock_cross_encoder.return_value = self.mock_model

        self.reranker = Reranker()

    def test_calculate_rerank_scores_empty_documents(self):
        scores = self.reranker.calculate_rerank_scores("query", [])
        self.assertEqual(scores, [])

    def test_calculate_rerank_scores_happy_path(self):
        self.mock_model.predict.return_value = [0.2, 0.8]

        documents = ["doc1", "doc2"]
        scores = self.reranker.calculate_rerank_scores("query", documents)

        self.mock_model.predict.assert_called_once()
        self.assertEqual(scores, [0.2, 0.8])

    def test_rerank_empty_results(self):
        results = self.reranker.rerank("query", [])
        self.assertEqual(results, [])

    def test_rerank_happy_path(self):
        self.reranker.calculate_rerank_scores = MagicMock(
            return_value=[0.9, 0.1]
        )

        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.2),
            RetrievalResult(content="B", metadata={}, relevance_score=0.3),
        ]

        reranked = self.reranker.rerank("query", results)

        self.assertEqual(len(reranked), 2)
        self.assertEqual(reranked[0].content, "A")
        self.assertGreater(
            reranked[0].relevance_score,
            reranked[1].relevance_score
        )


if __name__ == "__main__":
    unittest.main()
