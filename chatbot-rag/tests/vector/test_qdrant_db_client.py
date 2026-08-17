"""
Comprehensive unit tests for QdrantDBClient.

This test suite covers:
- Initialization and configuration
- Query collection operations
- Upsert operations with retry logic
- Delete operations (by ID and by filter)
- Count operations
- Collection management (ensure_collection)
- Error handling and retry mechanisms
- Edge cases and boundary conditions
"""

import os
import sys
import time
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.models import RetrievalResult
from src.vector.qdrant_db_client import QdrantDBClient


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    with patch.dict(os.environ, {"QDRANT_API_KEY": "test-api-key"}):
        yield


@pytest.fixture
def mock_config():
    """Mock configuration values."""
    config_values = {
        "vector.qdrant_url": "http://localhost",
        "vector.qdrant_port": 6333,
        "vector.qdrant_timeout": 60,
        "vector.qdrant_max_retries": 3,
        "vector.qdrant_retry_delay": 1.0,
        "vector.embedding_dimension": 384,
    }
    
    with patch("src.vector.qdrant_db_client.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.vector.qdrant_db_client.logger") as mock:
        yield mock


@pytest.fixture
def mock_qdrant_client():
    """Mock QdrantClient."""
    with patch("src.vector.qdrant_db_client.QdrantClient") as mock:
        yield mock


@pytest.fixture
def sample_query_points_response():
    """Sample query points response from Qdrant."""
    point1 = MagicMock()
    point1.payload = {
        "page_content": "Sample content 1",
        "document_name": "doc1.pdf",
        "chunk_type": "text",
        "page": 1
    }
    point1.score = 0.95
    
    point2 = MagicMock()
    point2.payload = {
        "page_content": "Sample content 2",
        "document_name": "doc2.pdf",
        "chunk_type": "text",
        "page": 2
    }
    point2.score = 0.87
    
    response = MagicMock()
    response.points = [point1, point2]
    return response


@pytest.fixture
def sample_points():
    """Sample points for upsert operations."""
    return [
        models.PointStruct(
            id="point-1",
            vector=[0.1] * 384,
            payload={"content": "Test content 1", "document_name": "test.pdf"}
        ),
        models.PointStruct(
            id="point-2",
            vector=[0.2] * 384,
            payload={"content": "Test content 2", "document_name": "test.pdf"}
        ),
    ]


@pytest.fixture
def qdrant_client(mock_env_vars, mock_config, mock_qdrant_client, mock_logger):
    """Create QdrantDBClient instance with mocked dependencies."""
    return QdrantDBClient()


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestQdrantDBClientInitialization:
    """Test QdrantDBClient initialization."""
    
    def test_initialization_with_config_values(
        self, mock_env_vars, mock_config, mock_qdrant_client, mock_logger
    ):
        """
        Test that client initializes with config values.
        
        Testing Concept: Test initialization
        """
        client = QdrantDBClient()
        
        assert client.url == "http://localhost"
        assert client.port == 6333
        assert client.api_key == "test-api-key"
        assert client.timeout == 60
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
    
    def test_initialization_creates_qdrant_client(
        self, mock_env_vars, mock_config, mock_qdrant_client, mock_logger
    ):
        """
        Test that QdrantClient is instantiated.
        
        Testing Concept: Test dependency creation
        """
        client = QdrantDBClient()
        
        mock_qdrant_client.assert_called_once_with(
            url="http://localhost",
            port=6333,
            api_key="test-api-key",
            timeout=60,
        )
    
    def test_initialization_logs_info(
        self, mock_env_vars, mock_config, mock_qdrant_client, mock_logger
    ):
        """
        Test that initialization logs info message.
        
        Testing Concept: Test logging
        """
        client = QdrantDBClient()
        
        mock_logger.info.assert_called_with(
            "QdrantClient initialized with timeout=%ds",
            60,
        )
    
    def test_initialization_with_missing_api_key(
        self, mock_config, mock_qdrant_client, mock_logger
    ):
        """
        Test initialization without API key.
        
        Testing Concept: Test missing environment variable
        """
        with patch.dict(os.environ, {}, clear=True):
            client = QdrantDBClient()
            
            assert client.api_key is None
    
    def test_initialization_with_default_timeout(
        self, mock_env_vars, mock_qdrant_client, mock_logger
    ):
        """
        Test initialization with default timeout.
        
        Testing Concept: Test default config values
        """
        config_values = {
            "vector.qdrant_url": "http://localhost",
            "vector.qdrant_port": 6333,
        }
        
        with patch("src.vector.qdrant_db_client.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: config_values.get(key, default)
            
            client = QdrantDBClient()
            
            # Should use default value of 60
            assert client.timeout == 60
    
    def test_initialization_with_custom_retry_settings(
        self, mock_env_vars, mock_qdrant_client, mock_logger
    ):
        """
        Test initialization with custom retry settings.
        
        Testing Concept: Test custom config values
        """
        config_values = {
            "vector.qdrant_url": "http://localhost",
            "vector.qdrant_port": 6333,
            "vector.qdrant_timeout": 30,
            "vector.qdrant_max_retries": 5,
            "vector.qdrant_retry_delay": 2.0,
        }
        
        with patch("src.vector.qdrant_db_client.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: config_values.get(key, default)
            
            client = QdrantDBClient()
            
            assert client.max_retries == 5
            assert client.retry_delay == 2.0

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("QDRANT_HOST", "http://test-host")
        monkeypatch.setenv("QDRANT_PORT", "6333")

        with (
            patch("src.vector.qdrant_db_client.QdrantClient") as mock_qdrant,
            patch("src.vector.qdrant_db_client.get_config") as mock_config,
        ):
            mock_config.side_effect = lambda key, default=None: {
                "vector.qdrant_url": "http://localhost",
                "vector.qdrant_port": 6333,
            }.get(key, default)

            client = QdrantDBClient()

            mock_qdrant.assert_called_once_with(
                url="http://test-host",
                port=6333,
                api_key=None,
                timeout=60,
            )

            assert client.url == "http://test-host"
            assert client.port == 6333
            assert isinstance(client.port, int)

    def test_env_override_config(self, monkeypatch):
        monkeypatch.delenv("QDRANT_HOST", raising=False)
        monkeypatch.delenv("QDRANT_PORT", raising=False)

        with (
            patch("src.vector.qdrant_db_client.QdrantClient"),
            patch("src.vector.qdrant_db_client.get_config") as mock_config,
        ):
            mock_config.side_effect = lambda key, default=None: {
                "vector.qdrant_url": "http://localhost",
                "vector.qdrant_port": 6333,
            }.get(key, default)

            client = QdrantDBClient()

            assert client.url == "http://localhost"
            assert client.port == 6333



# ============================================================================
# TEST CLASS: Query Collection Tests
# ============================================================================


class TestQueryCollection:
    """Test query_collection functionality."""
    
    def test_query_collection_returns_results(
        self, qdrant_client, sample_query_points_response
    ):
        """
        Test that query_collection returns formatted results.
        
        Testing Concept: Test happy path
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        query_embedding = [0.1] * 384
        results = qdrant_client.query_collection(
            "test_collection",
            query_embedding,
            top_k=10
        )
        
        assert len(results) == 2
        assert isinstance(results[0], RetrievalResult)
        assert results[0].content == "Sample content 1"
        assert results[0].relevance_score == 0.95
        assert results[0].metadata["document_name"] == "doc1.pdf"
    
    def test_query_collection_calls_qdrant_with_correct_params(
        self, qdrant_client, sample_query_points_response
    ):
        """
        Test that query_collection calls Qdrant with correct parameters.
        
        Testing Concept: Test method invocation
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        query_embedding = [0.1] * 384
        qdrant_client.query_collection(
            "test_collection",
            query_embedding,
            top_k=5
        )
        
        qdrant_client.client.query_points.assert_called_once_with(
            collection_name="test_collection",
            query=query_embedding,
            limit=5,
            with_payload=True,
        )
    
    def test_query_collection_converts_numpy_array(
        self, qdrant_client, sample_query_points_response
    ):
        """
        Test that numpy arrays are converted to lists.
        
        Testing Concept: Test data type conversion
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        # Mock numpy array with tolist method
        mock_numpy_array = MagicMock()
        mock_numpy_array.tolist.return_value = [0.1] * 384
        
        qdrant_client.query_collection(
            "test_collection",
            mock_numpy_array,
            top_k=10
        )
        
        # Verify tolist was called
        mock_numpy_array.tolist.assert_called_once()
    
    def test_query_collection_handles_content_key_variations(
        self, qdrant_client
    ):
        """
        Test handling of both 'page_content' and 'content' keys.
        
        Testing Concept: Test key variations
        """
        # Response with 'content' key instead of 'page_content'
        point = MagicMock()
        point.payload = {
            "content": "Content via content key",
            "document_name": "doc.pdf"
        }
        point.score = 0.9
        
        response = MagicMock()
        response.points = [point]
        
        qdrant_client.client.query_points.return_value = response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=10
        )
        
        assert results[0].content == "Content via content key"
    
    def test_query_collection_handles_missing_content(
        self, qdrant_client
    ):
        """
        Test handling when neither 'page_content' nor 'content' exists.
        
        Testing Concept: Test missing keys
        """
        point = MagicMock()
        point.payload = {
            "document_name": "doc.pdf"
            # No content key
        }
        point.score = 0.9
        
        response = MagicMock()
        response.points = [point]
        
        qdrant_client.client.query_points.return_value = response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=10
        )
        
        # Should default to empty string
        assert results[0].content == ""
    
    def test_query_collection_handles_empty_payload(
        self, qdrant_client
    ):
        """
        Test handling of points with None or empty payload.
        
        Testing Concept: Test empty payload
        """
        point = MagicMock()
        point.payload = None
        point.score = 0.9
        
        response = MagicMock()
        response.points = [point]
        
        qdrant_client.client.query_points.return_value = response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=10
        )
        
        assert results[0].content == ""
        assert results[0].metadata == {}
    
    def test_query_collection_with_empty_results(
        self, qdrant_client
    ):
        """
        Test query with no results.
        
        Testing Concept: Test empty results
        """
        response = MagicMock()
        response.points = []
        
        qdrant_client.client.query_points.return_value = response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=10
        )
        
        assert results == []
    
    def test_query_collection_excludes_content_from_metadata(
        self, qdrant_client
    ):
        """
        Test that content keys are excluded from metadata.
        
        Testing Concept: Test metadata extraction
        """
        point = MagicMock()
        point.payload = {
            "page_content": "Sample content",
            "content": "Alternative content",
            "document_name": "doc.pdf",
            "page": 1
        }
        point.score = 0.9
        
        response = MagicMock()
        response.points = [point]
        
        qdrant_client.client.query_points.return_value = response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=10
        )
        
        # Content keys should not be in metadata
        assert "page_content" not in results[0].metadata
        assert "content" not in results[0].metadata
        assert "document_name" in results[0].metadata
        assert "page" in results[0].metadata
    
    def test_query_collection_with_default_top_k(
        self, qdrant_client, sample_query_points_response
    ):
        """
        Test query with default top_k value.
        
        Testing Concept: Test default parameter
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384
        )
        
        # Default top_k is 30
        qdrant_client.client.query_points.assert_called_once()
        call_kwargs = qdrant_client.client.query_points.call_args[1]
        assert call_kwargs["limit"] == 30


# ============================================================================
# TEST CLASS: Upsert Tests
# ============================================================================


class TestUpsert:
    """Test upsert functionality with retry logic."""
    
    def test_upsert_success_on_first_try(
        self, qdrant_client, sample_points, mock_logger
    ):
        """
        Test successful upsert on first attempt.
        
        Testing Concept: Test happy path
        """
        qdrant_client.upsert("test_collection", sample_points)
        
        qdrant_client.client.upsert.assert_called_once_with(
            collection_name="test_collection",
            points=sample_points
        )
        
        mock_logger.info.assert_called_with(
            "Successfully upserted %d points to collection '%s'",
            2,
            "test_collection",
        )
    
    def test_upsert_retries_on_failure(
        self, qdrant_client, sample_points, mock_logger
    ):
        """
        Test that upsert retries on ResponseHandlingException.
        
        Testing Concept: Test retry logic
        """
        # Fail twice, succeed on third attempt
        qdrant_client.client.upsert.side_effect = [
            ResponseHandlingException("Connection error"),
            ResponseHandlingException("Timeout"),
            None  # Success
        ]
        
        with patch("src.vector.qdrant_db_client.time.sleep") as mock_sleep:
            qdrant_client.upsert("test_collection", sample_points)
            
            # Should have attempted 3 times
            assert qdrant_client.client.upsert.call_count == 3
            
            # Should have slept twice (exponential backoff: 1s, 2s)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1.0)  # First retry: 1.0 * 2^0
            mock_sleep.assert_any_call(2.0)  # Second retry: 1.0 * 2^1
    
    def test_upsert_raises_after_max_retries(
        self, qdrant_client, sample_points, mock_logger
    ):
        """
        Test that upsert raises exception after max retries.
        
        Testing Concept: Test retry exhaustion
        """
        error = ResponseHandlingException("Persistent error")
        qdrant_client.client.upsert.side_effect = error
        
        with patch("src.vector.qdrant_db_client.time.sleep"):
            with pytest.raises(ResponseHandlingException):
                qdrant_client.upsert("test_collection", sample_points)
            
            # Should have attempted max_retries + 1 times (3 + 1 = 4)
            assert qdrant_client.client.upsert.call_count == 4
            
            # Should log error
            mock_logger.error.assert_called_with(
                "Failed to upsert points after %d attempts: %s",
                4,
                "Persistent error",
            )
    
    def test_upsert_logs_retry_attempts(
        self, qdrant_client, sample_points, mock_logger
    ):
        """
        Test that retry attempts are logged.
        
        Testing Concept: Test logging
        """
        qdrant_client.client.upsert.side_effect = [
            ResponseHandlingException("Error 1"),
            None  # Success on second attempt
        ]
        
        with patch("src.vector.qdrant_db_client.time.sleep"):
            qdrant_client.upsert("test_collection", sample_points)
            
            mock_logger.warning.assert_called_with(
                "Upsert attempt %d failed, retrying in %.1fs: %s",
                1,
                1.0,
                "Error 1",
            )
    
    def test_upsert_exponential_backoff(
        self, qdrant_client, sample_points
    ):
        """
        Test exponential backoff calculation.
        
        Testing Concept: Test backoff strategy
        """
        qdrant_client.client.upsert.side_effect = [
            ResponseHandlingException("Error 1"),
            ResponseHandlingException("Error 2"),
            ResponseHandlingException("Error 3"),
            None  # Success
        ]
        
        with patch("src.vector.qdrant_db_client.time.sleep") as mock_sleep:
            qdrant_client.upsert("test_collection", sample_points)
            
            # Verify exponential backoff: 1s, 2s, 4s
            calls = mock_sleep.call_args_list
            assert calls[0][0][0] == 1.0  # 1.0 * 2^0
            assert calls[1][0][0] == 2.0  # 1.0 * 2^1
            assert calls[2][0][0] == 4.0  # 1.0 * 2^2
    
    def test_upsert_with_empty_points_list(
        self, qdrant_client, mock_logger
    ):
        """
        Test upsert with empty points list.
        
        Testing Concept: Test empty input
        """
        qdrant_client.upsert("test_collection", [])
        
        qdrant_client.client.upsert.assert_called_once()
        mock_logger.info.assert_called_with(
            "Successfully upserted %d points to collection '%s'",
            0,
            "test_collection",
        )
    
    def test_upsert_with_single_point(
        self, qdrant_client
    ):
        """
        Test upsert with single point.
        
        Testing Concept: Test single item
        """
        single_point = [
            models.PointStruct(
                id="point-1",
                vector=[0.1] * 384,
                payload={"content": "Single point"}
            )
        ]
        
        qdrant_client.upsert("test_collection", single_point)
        
        qdrant_client.client.upsert.assert_called_once()


# ============================================================================
# TEST CLASS: Delete Tests
# ============================================================================


class TestDelete:
    """Test delete operations."""
    
    def test_delete_by_ids(self, qdrant_client):
        """
        Test deleting points by IDs.
        
        Testing Concept: Test delete by ID
        """
        point_ids = ["point-1", "point-2", "point-3"]
        
        qdrant_client.delete("test_collection", point_ids)
        
        qdrant_client.client.delete.assert_called_once()
        call_args = qdrant_client.client.delete.call_args
        
        assert call_args[1]["collection_name"] == "test_collection"
        assert isinstance(call_args[1]["points_selector"], models.PointIdsList)
    
    def test_delete_with_empty_ids(self, qdrant_client):
        """
        Test delete with empty ID list.
        
        Testing Concept: Test empty input
        """
        qdrant_client.delete("test_collection", [])
        
        qdrant_client.client.delete.assert_called_once()
    
    def test_delete_with_single_id(self, qdrant_client):
        """
        Test delete with single ID.
        
        Testing Concept: Test single item
        """
        qdrant_client.delete("test_collection", ["point-1"])
        
        qdrant_client.client.delete.assert_called_once()
    
    def test_delete_by_filter(self, qdrant_client):
        """
        Test deleting points by metadata filter.
        
        Testing Concept: Test delete by filter
        """
        qdrant_client.delete_by_filter(
            "test_collection",
            key="document_name",
            value="test.pdf"
        )
        
        qdrant_client.client.delete.assert_called_once()
        call_args = qdrant_client.client.delete.call_args
        
        assert call_args[1]["collection_name"] == "test_collection"
        assert isinstance(call_args[1]["points_selector"], models.FilterSelector)
    
    def test_delete_by_filter_constructs_correct_filter(
        self, qdrant_client
    ):
        """
        Test that delete_by_filter constructs correct Qdrant filter.
        
        Testing Concept: Test filter construction
        """
        qdrant_client.delete_by_filter(
            "test_collection",
            key="status",
            value="archived"
        )
        
        call_args = qdrant_client.client.delete.call_args[1]
        filter_selector = call_args["points_selector"]
        
        # Verify filter structure
        assert isinstance(filter_selector, models.FilterSelector)
    
    def test_delete_by_filter_with_special_characters(
        self, qdrant_client
    ):
        """
        Test delete_by_filter with special characters in value.
        
        Testing Concept: Test special character handling
        """
        qdrant_client.delete_by_filter(
            "test_collection",
            key="document_name",
            value="file-with_special.chars.pdf"
        )
        
        qdrant_client.client.delete.assert_called_once()


# ============================================================================
# TEST CLASS: Count Tests
# ============================================================================


class TestCount:
    """Test count operations."""
    
    def test_count_returns_number(self, qdrant_client):
        """
        Test that count returns the number of points.
        
        Testing Concept: Test count operation
        """
        mock_count_response = MagicMock()
        mock_count_response.count = 42
        
        qdrant_client.client.count.return_value = mock_count_response
        
        result = qdrant_client.count("test_collection")
        
        assert result == 42
        qdrant_client.client.count.assert_called_once_with(
            collection_name="test_collection"
        )
    
    def test_count_with_empty_collection(self, qdrant_client):
        """
        Test count with empty collection.
        
        Testing Concept: Test empty collection
        """
        mock_count_response = MagicMock()
        mock_count_response.count = 0
        
        qdrant_client.client.count.return_value = mock_count_response
        
        result = qdrant_client.count("empty_collection")
        
        assert result == 0
    
    def test_count_with_large_number(self, qdrant_client):
        """
        Test count with large number of points.
        
        Testing Concept: Test large values
        """
        mock_count_response = MagicMock()
        mock_count_response.count = 1000000
        
        qdrant_client.client.count.return_value = mock_count_response
        
        result = qdrant_client.count("large_collection")
        
        assert result == 1000000


# ============================================================================
# TEST CLASS: Ensure Collection Tests
# ============================================================================


class TestEnsureCollection:
    """Test ensure_collection functionality."""
    
    def test_ensure_collection_creates_if_not_exists(
        self, qdrant_client, mock_logger
    ):
        """
        Test that collection is created if it doesn't exist.
        
        Testing Concept: Test collection creation
        """
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        
        qdrant_client.ensure_collection("new_collection")
        
        # Should attempt to get collection
        qdrant_client.client.get_collection.assert_called_once_with("new_collection")
        
        # Should create collection
        qdrant_client.client.create_collection.assert_called_once()
        
        # Should create index
        qdrant_client.client.create_payload_index.assert_called_once()
    
    def test_ensure_collection_does_not_create_if_exists(
        self, qdrant_client
    ):
        """
        Test that collection is not created if it exists.
        
        Testing Concept: Test idempotency
        """
        # Collection exists
        qdrant_client.client.get_collection.return_value = MagicMock()
        
        qdrant_client.ensure_collection("existing_collection")
        
        # Should not create collection
        qdrant_client.client.create_collection.assert_not_called()
        
        # Should still create index (idempotent operation)
        qdrant_client.client.create_payload_index.assert_called_once()
    
    def test_ensure_collection_creates_with_correct_config(
        self, qdrant_client
    ):
        """
        Test that collection is created with correct configuration.
        
        Testing Concept: Test configuration parameters
        """
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        
        qdrant_client.ensure_collection("new_collection")
        
        # Verify create_collection call
        call_args = qdrant_client.client.create_collection.call_args
        
        assert call_args[1]["collection_name"] == "new_collection"
        assert isinstance(call_args[1]["vectors_config"], models.VectorParams)
    
    def test_ensure_collection_creates_index_on_document_name(
        self, qdrant_client
    ):
        """
        Test that index is created on document_name field.
        
        Testing Concept: Test index creation
        """
        qdrant_client.client.get_collection.return_value = MagicMock()
        
        qdrant_client.ensure_collection("test_collection")
        
        qdrant_client.client.create_payload_index.assert_called_once_with(
            collection_name="test_collection",
            field_name="document_name",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    
    def test_ensure_collection_logs_debug_on_not_found(
        self, qdrant_client, mock_logger
    ):
        """
        Test that exception is logged when collection doesn't exist.
        
        Testing Concept: Test logging
        """
        error = Exception("Collection not found")
        qdrant_client.client.get_collection.side_effect = error
        
        qdrant_client.ensure_collection("new_collection")
        
        mock_logger.debug.assert_called_once_with(error)
    
    def test_ensure_collection_uses_config_dimension(
        self, qdrant_client
    ):
        """
        Test that collection uses embedding dimension from config.
        
        Testing Concept: Test config usage
        """
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        
        qdrant_client.ensure_collection("new_collection")
        
        # Verify vectors_config uses dimension from config (384)
        call_args = qdrant_client.client.create_collection.call_args
        vectors_config = call_args[1]["vectors_config"]
        
        assert vectors_config.size == 384
        assert vectors_config.distance == models.Distance.COSINE


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_workflow_query_and_upsert(
        self, qdrant_client, sample_query_points_response, sample_points
    ):
        """
        Test complete workflow: query, upsert, query again.
        
        Testing Concept: Integration test
        """
        # First query
        qdrant_client.client.query_points.return_value = sample_query_points_response
        results = qdrant_client.query_collection("test_collection", [0.1] * 384)
        assert len(results) == 2
        
        # Upsert new points
        qdrant_client.upsert("test_collection", sample_points)
        
        # Query again
        results2 = qdrant_client.query_collection("test_collection", [0.2] * 384)
        assert isinstance(results2, list)
    
    def test_collection_lifecycle(self, qdrant_client):
        """
        Test complete collection lifecycle.
        
        Testing Concept: Integration test
        """
        # Ensure collection exists
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        qdrant_client.ensure_collection("lifecycle_collection")
        
        # Count (should be 0 initially)
        mock_count = MagicMock()
        mock_count.count = 0
        qdrant_client.client.count.return_value = mock_count
        count = qdrant_client.count("lifecycle_collection")
        assert count == 0
        
        # Upsert points
        points = [
            models.PointStruct(
                id="p1",
                vector=[0.1] * 384,
                payload={"doc": "test.pdf"}
            )
        ]
        qdrant_client.upsert("lifecycle_collection", points)
        
        # Delete by filter
        qdrant_client.delete_by_filter(
            "lifecycle_collection",
            "doc",
            "test.pdf"
        )


# ============================================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""
    
    def test_query_with_very_large_top_k(
        self, qdrant_client, sample_query_points_response
    ):
        """
        Test query with very large top_k value.
        
        Testing Concept: Test boundary value
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=10000
        )
        
        assert isinstance(results, list)
    
    def test_query_with_zero_dimensional_embedding(
        self, qdrant_client, sample_query_points_response
    ):
        """
        Test query with empty embedding.
        
        Testing Concept: Test empty embedding
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [],
            top_k=10
        )
        
        assert isinstance(results, list)
    
    def test_upsert_with_none_points(self, qdrant_client):
        """
        Test upsert behavior with None points.
        
        Testing Concept: Test None input
        """
        # This should raise an error in actual usage
        # but test that the method is called
        with pytest.raises(Exception):
            qdrant_client.upsert("test_collection", None)
    
    def test_delete_with_none_ids(self, qdrant_client):
        """
        Test delete with None IDs.
        
        Testing Concept: Test None input
        """
        with pytest.raises(Exception):
            qdrant_client.delete("test_collection", None)
    
    def test_query_collection_with_malformed_response(
        self, qdrant_client
    ):
        """
        Test handling of malformed response from Qdrant.
        
        Testing Concept: Test unexpected response
        """
        # Response without points attribute
        bad_response = MagicMock()
        bad_response.points = None
        
        qdrant_client.client.query_points.return_value = bad_response
        
        with pytest.raises(TypeError):
            qdrant_client.query_collection("test_collection", [0.1] * 384)
    
    def test_ensure_collection_with_network_error(
        self, qdrant_client
    ):
        """
        Test ensure_collection when network error occurs.
        
        Testing Concept: Test network failure
        """
        qdrant_client.client.get_collection.side_effect = Exception("Network error")
        qdrant_client.client.create_collection.side_effect = Exception("Still failing")
        
        with pytest.raises(Exception):
            qdrant_client.ensure_collection("test_collection")
    
    def test_upsert_with_mixed_success_failure(
        self, qdrant_client, sample_points, mock_logger
    ):
        """
        Test upsert that fails then succeeds on retry.
        
        Testing Concept: Test recovery from transient failure
        """
        # First call fails, second succeeds
        qdrant_client.client.upsert.side_effect = [
            ResponseHandlingException("Transient error"),
            None
        ]
        
        with patch("src.vector.qdrant_db_client.time.sleep"):
            qdrant_client.upsert("test_collection", sample_points)
            
            # Should succeed after retry
            assert qdrant_client.client.upsert.call_count == 2
            mock_logger.info.assert_called()


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("top_k", [1, 5, 10, 50, 100])
    def test_query_with_various_top_k_values(
        self, qdrant_client, sample_query_points_response, top_k
    ):
        """
        Test query with various top_k values.
        
        Testing Concept: Parameterized top_k testing
        """
        qdrant_client.client.query_points.return_value = sample_query_points_response
        
        results = qdrant_client.query_collection(
            "test_collection",
            [0.1] * 384,
            top_k=top_k
        )
        
        call_kwargs = qdrant_client.client.query_points.call_args[1]
        assert call_kwargs["limit"] == top_k
    
    @pytest.mark.parametrize("retry_count", [0, 1, 2, 3])
    def test_upsert_with_various_retry_counts(
        self, qdrant_client, sample_points, retry_count
    ):
        """
        Test upsert with various numbers of retries.
        
        Testing Concept: Parameterized retry testing
        """
        # Fail retry_count times, then succeed
        side_effects = [ResponseHandlingException(f"Error {i}") for i in range(retry_count)]
        side_effects.append(None)  # Success
        
        qdrant_client.client.upsert.side_effect = side_effects
        
        with patch("src.vector.qdrant_db_client.time.sleep"):
            qdrant_client.upsert("test_collection", sample_points)
            
            assert qdrant_client.client.upsert.call_count == retry_count + 1
    
    @pytest.mark.parametrize("collection_name", [
        "test_collection",
        "collection-with-dashes",
        "collection_with_underscores",
        "CollectionWithCaps",
        "123numeric"
    ])
    def test_operations_with_various_collection_names(
        self, qdrant_client, collection_name
    ):
        """
        Test operations with various collection name formats.
        
        Testing Concept: Parameterized collection names
        """
        # Test count operation with various names
        mock_count = MagicMock()
        mock_count.count = 10
        qdrant_client.client.count.return_value = mock_count
        
        result = qdrant_client.count(collection_name)
        
        assert result == 10
        qdrant_client.client.count.assert_called_with(
            collection_name=collection_name
        )


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.vector.qdrant_db_client",
        "--cov-report=term-missing"
    ])


