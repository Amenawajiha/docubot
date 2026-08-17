#!/usr/bin/env python3
"""
Pytest tests to verify Qdrant connection and timeout fixes.
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ingestion.qdrant_loader import QdrantLoader
from src.vector.qdrant_db_client import QdrantDBClient
from src.utils import logger


class TestQdrantConnection:
    """Test Qdrant connection and timeout configuration."""

    def test_qdrant_client_initialization(self):
        """Test that QdrantClient initializes with correct timeout configuration."""
        client = QdrantDBClient()

        # Verify timeout configuration is loaded
        assert client.timeout == 60
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.client is not None

        logger.info("✅ QdrantClient initialized with correct timeout configuration")

    def test_qdrant_loader_initialization(self):
        """Test that QdrantLoader initializes successfully."""
        loader = QdrantLoader()

        assert loader.collection_name == "schengen_visa_docs"
        assert loader.qdrant_db_client is not None
        assert loader.embedding_manager is not None
        assert loader.chunker is not None

        logger.info("✅ QdrantLoader initialized successfully")

    def test_collection_stats(self):
        """Test retrieving collection statistics."""
        loader = QdrantLoader()

        try:
            stats = loader.get_collection_stats()

            # Verify stats structure
            assert "collection_name" in stats
            assert "total_documents" in stats
            assert "embedding_model" in stats
            assert "provider" in stats

            logger.info("✅ Collection stats retrieved: %s", stats)

        except Exception as e:
            pytest.fail(f"Failed to get collection stats: {e}")


class TestQdrantRetryLogic:
    """Test retry logic for Qdrant operations."""

    @patch("src.vector.qdrant_db_client.QdrantClient")
    def test_upsert_retry_success_on_second_attempt(self, mock_qdrant_client):
        """Test that upsert retries on failure and succeeds on second attempt."""
        from qdrant_client.http.exceptions import ResponseHandlingException

        # Mock client that fails first time, succeeds second time
        mock_client_instance = MagicMock()
        mock_client_instance.upsert.side_effect = [
            ResponseHandlingException("Connection timeout"),
            None,  # Success on second attempt
        ]
        mock_qdrant_client.return_value = mock_client_instance

        client = QdrantDBClient()

        # Should not raise exception due to retry logic
        client.upsert("test_collection", [])

        # Verify upsert was called twice
        assert mock_client_instance.upsert.call_count == 2
        logger.info("✅ Retry logic works: succeeded on second attempt")

    @patch("src.vector.qdrant_db_client.QdrantClient")
    def test_upsert_retry_exhaustion(self, mock_qdrant_client):
        """Test that upsert fails after max retries."""
        from qdrant_client.http.exceptions import ResponseHandlingException

        # Mock client that always fails
        mock_client_instance = MagicMock()
        mock_client_instance.upsert.side_effect = ResponseHandlingException(
            "Persistent connection error"
        )
        mock_qdrant_client.return_value = mock_client_instance

        client = QdrantDBClient()

        # Should raise exception after max retries
        with pytest.raises(
            ResponseHandlingException, match="Persistent connection error"
        ):
            client.upsert("test_collection", [])

        # Verify upsert was called max_retries + 1 times
        assert mock_client_instance.upsert.call_count == 4  # 3 retries + 1 initial
        logger.info("✅ Retry exhaustion works: failed after 4 attempts")


class TestDocumentProcessing:
    """Test document processing with Qdrant integration."""

    @pytest.mark.skipif(
        not Path("documents/Schengen Visa FAQs.docx").exists(),
        reason="Test document not found",
    )
    def test_document_processing_success(self):
        """Test successful document processing."""
        test_doc_path = Path("documents/Schengen Visa FAQs.docx")

        loader = QdrantLoader()

        # Read file bytes
        with open(test_doc_path, "rb") as f:
            file_bytes = f.read()

        # Process document
        start_time = time.time()
        result = loader.process_document(file_bytes, test_doc_path.name)
        end_time = time.time()

        # Verify successful processing
        assert result["status"] == "success"
        assert result["file"] == test_doc_path.name
        assert result["chunks_created"] > 0
        assert result["chunks_stored"] > 0
        assert result["content_size"] > 0

        logger.info(
            "✅ Document processed successfully in %.1fs", end_time - start_time
        )
        logger.info("   Chunks created: %d", result["chunks_created"])
        logger.info("   Chunks stored: %d", result["chunks_stored"])

    def test_document_processing_invalid_file(self):
        """Test document processing with invalid file bytes."""
        loader = QdrantLoader()

        # Process invalid file bytes
        result = loader.process_document(b"invalid docx content", "test.docx")

        # Should fail gracefully
        assert result["status"] == "error"
        assert "error" in result

        logger.info("✅ Invalid file handled gracefully: %s", result["error"])


# Integration test - only run if explicitly requested
@pytest.mark.integration
class TestIntegration:
    """Integration tests that require actual Qdrant connection."""

    def test_full_integration(self):
        """Test full integration with real Qdrant connection."""
        # This test only runs with: pytest -m integration
        loader = QdrantLoader()

        # Test connection
        stats = loader.get_collection_stats()
        assert "collection_name" in stats

        logger.info("✅ Full integration test passed")


if __name__ == "__main__":
    # Allow running as script for backward compatibility
    pytest.main([__file__, "-v"])
