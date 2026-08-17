"""Unit tests for QdrantCollectionManager in src.vector.collection_manager."""

import pytest
from unittest.mock import MagicMock, patch

from src.vector.collection_manager import QdrantCollectionManager


@pytest.fixture(autouse=True)
def reset_collection_manager_loader():
    """Reset the cached loader instance on QdrantCollectionManager before each test."""
    QdrantCollectionManager._loader = None
    yield
    QdrantCollectionManager._loader = None


def test_collection_name_formatting():
    """Test deterministic collection name generation for standard and edge case inputs."""
    # Happy Path
    name = QdrantCollectionManager.collection_name("ws123", "bot456")
    assert name == "workspace_ws123_chatbot_bot456"

    # Edge Cases: empty strings, numbers as strings
    empty_name = QdrantCollectionManager.collection_name("", "")
    assert empty_name == "workspace__chatbot_"

    special_name = QdrantCollectionManager.collection_name("workspace-1", "chatbot_2")
    assert special_name == "workspace_workspace-1_chatbot_chatbot_2"


@patch("src.vector.collection_manager.QdrantLoader")
def test_get_loader_lazy_initialization(mock_qdrant_loader):
    """Test lazy initialization and caching of QdrantLoader singleton."""
    mock_instance = MagicMock()
    mock_qdrant_loader.return_value = mock_instance

    # First call initializes loader
    loader1 = QdrantCollectionManager._get_loader()
    assert loader1 == mock_instance
    mock_qdrant_loader.assert_called_once()

    # Second call returns cached instance without re-instantiating
    loader2 = QdrantCollectionManager._get_loader()
    assert loader2 == mock_instance
    mock_qdrant_loader.assert_called_once()


@patch("src.vector.qdrant_db_client.QdrantDBClient")
def test_ensure_collection(mock_db_client_cls):
    """Test ensure_collection formats name and delegates to QdrantDBClient."""
    mock_client = MagicMock()
    mock_db_client_cls.return_value = mock_client

    result = QdrantCollectionManager.ensure_collection("ws_test", "bot_test")

    expected_name = "workspace_ws_test_chatbot_bot_test"
    assert result == expected_name
    mock_db_client_cls.assert_called_once()
    mock_client.ensure_collection.assert_called_once_with(expected_name)


@patch.object(QdrantCollectionManager, "_get_loader")
def test_delete_points_for_document_string_and_int(mock_get_loader):
    """Test delete_points_for_document casts document_id to string and calls loader."""
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader

    # Happy Path with string ID
    QdrantCollectionManager.delete_points_for_document("col_name", "doc_123")
    mock_loader.delete_document_chunks.assert_called_with("doc_123")

    # Edge Case with integer ID
    QdrantCollectionManager.delete_points_for_document("col_name", 999)
    mock_loader.delete_document_chunks.assert_called_with("999")


@patch.object(QdrantCollectionManager, "_get_loader")
def test_delete_collection_success(mock_get_loader):
    """Test delete_collection successfully deletes a collection via Qdrant client."""
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader

    QdrantCollectionManager.delete_collection("workspace_ws1_chatbot_bot1")

    mock_loader.qdrant_db_client.client.delete_collection.assert_called_once_with(
        "workspace_ws1_chatbot_bot1"
    )


@patch.object(QdrantCollectionManager, "_get_loader")
def test_delete_collection_handles_exception(mock_get_loader):
    """Test delete_collection silently catches exceptions (e.g. when collection does not exist)."""
    mock_loader = MagicMock()
    mock_loader.qdrant_db_client.client.delete_collection.side_effect = Exception("Collection not found")
    mock_get_loader.return_value = mock_loader

    # Should not raise exception
    QdrantCollectionManager.delete_collection("non_existent_collection")
    mock_loader.qdrant_db_client.client.delete_collection.assert_called_once_with("non_existent_collection")
