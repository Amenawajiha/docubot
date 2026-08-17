"""
Comprehensive unit tests for streamlit_app.py - FIXED VERSION

This test suite covers:
- Page configuration and initialization
- QdrantLoader caching
- Stats display
- Upload section display
- Document queue display
- Error handling
- Main function orchestration
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ============================================================================
# CRITICAL: Patch Streamlit BEFORE importing the module
# ============================================================================

mock_streamlit = MagicMock()
sys.modules['streamlit'] = mock_streamlit

# Mock all Streamlit components
mock_streamlit.set_page_config = MagicMock()
mock_streamlit.title = MagicMock()
mock_streamlit.markdown = MagicMock()
mock_streamlit.error = MagicMock()
mock_streamlit.exception = MagicMock()
mock_streamlit.cache_resource = lambda func: func  # Pass-through decorator


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_streamlit_mocks():
    """Reset all Streamlit mocks before each test."""
    mock_streamlit.set_page_config.reset_mock()
    mock_streamlit.title.reset_mock()
    mock_streamlit.markdown.reset_mock()
    mock_streamlit.error.reset_mock()
    mock_streamlit.exception.reset_mock()
    yield


@pytest.fixture
def mock_qdrant_loader():
    """Mock QdrantLoader."""
    mock_loader = MagicMock()
    mock_loader.get_collection_stats.return_value = {
        "collection_name": "test_collection",
        "total_documents": 100,
        "embedding_model": "test-model",
        "provider": "Qdrant Cloud"
    }
    mock_loader.get_unique_document_count.return_value = 10
    return mock_loader


@pytest.fixture
def mock_environment():
    """Mock environment variables."""
    with patch.dict(os.environ, {"QDRANT_URL": "http://localhost:6333"}, clear=False):
        yield


# ============================================================================
# COMPREHENSIVE MOCK SETUP - Applied to ALL tests
# ============================================================================


@pytest.fixture(autouse=True)
def comprehensive_mocks(mock_qdrant_loader):
    """
    Apply comprehensive mocks to ALL tests automatically.
    This ensures we never create real instances.
    """
    with patch("src.ingestion.streamlit_app.QdrantLoader") as mock_loader_class, \
         patch("src.ingestion.streamlit_app.display_collection_stats") as mock_stats, \
         patch("src.ingestion.streamlit_app.display_upload_section") as mock_upload, \
         patch("src.ingestion.streamlit_app.display_document_queue") as mock_queue, \
         patch("src.ingestion.streamlit_app.get_config") as mock_config, \
         patch("src.ingestion.streamlit_app.create_log_file") as mock_log:
        
        # Setup default return values
        mock_loader_class.return_value = mock_qdrant_loader
        mock_config.side_effect = lambda key, default=None: {
            "streamlit.page_title": "Ingestion Pipeline",
            "streamlit.page_icon": "📚",
            "streamlit.layout": "wide",
        }.get(key, default)
        
        yield {
            'loader_class': mock_loader_class,
            'loader_instance': mock_qdrant_loader,
            'stats': mock_stats,
            'upload': mock_upload,
            'queue': mock_queue,
            'config': mock_config,
            'log': mock_log
        }


# ============================================================================
# TEST CLASS: Main Function - Happy Path
# ============================================================================


class TestMainFunctionHappyPath:
    """Test main function normal execution flow."""
    
    def test_main_displays_title_and_description(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main displays title and description."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        mock_streamlit.title.assert_called_once_with("Ingestion Pipeline")
        assert mock_streamlit.markdown.call_count >= 2
    
    def test_main_initializes_qdrant_loader(self, comprehensive_mocks, mock_environment):
        """Test that main initializes QdrantLoader."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        comprehensive_mocks['loader_class'].assert_called()
    
    def test_main_gets_collection_stats(self, comprehensive_mocks, mock_environment):
        """Test that main retrieves collection stats."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        comprehensive_mocks['loader_instance'].get_collection_stats.assert_called_once()
    
    def test_main_counts_unique_documents(self, comprehensive_mocks, mock_environment):
        """Test that main counts unique documents."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        comprehensive_mocks['loader_instance'].get_unique_document_count.assert_called_once()
    
    def test_main_displays_collection_stats(self, comprehensive_mocks, mock_environment):
        """Test that main displays collection stats."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        comprehensive_mocks['stats'].assert_called_once()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert "total_chunks" in call_args
        assert "unique_documents" in call_args
        assert "connection_type" in call_args
    
    def test_main_stats_display_includes_correct_values(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that stats display includes correct values from loader."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert call_args["total_chunks"] == 100
        assert call_args["unique_documents"] == 10
    
    def test_main_displays_upload_section(self, comprehensive_mocks, mock_environment):
        """Test that main displays upload section."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        comprehensive_mocks['upload'].assert_called_once_with(
            comprehensive_mocks['loader_instance']
        )
    
    def test_main_displays_document_queue(self, comprehensive_mocks, mock_environment):
        """Test that main displays document queue."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        comprehensive_mocks['queue'].assert_called_once()
        call_kwargs = comprehensive_mocks['queue'].call_args[1]
        assert call_kwargs['qdrant_loader'] == comprehensive_mocks['loader_instance']


# ============================================================================
# TEST CLASS: Connection Type Detection
# ============================================================================


class TestMainConnectionTypeDetection:
    """Test connection type detection logic."""
    
    def test_main_detects_local_connection_from_localhost(
        self, comprehensive_mocks
    ):
        """Test that main detects local connection when localhost in URL."""
        with patch.dict(os.environ, {"QDRANT_URL": "http://localhost:6333"}):
            from src.ingestion.streamlit_app import main
            
            main()
            
            call_args = comprehensive_mocks['stats'].call_args[0][0]
            assert call_args["connection_type"] == "Local (Docker)"
    
    def test_main_detects_cloud_connection_from_127(
        self, comprehensive_mocks
    ):
        """Test that 127.0.0.1 is detected as Cloud (doesn't contain 'localhost')."""
        with patch.dict(os.environ, {"QDRANT_URL": "http://127.0.0.1:6333"}):
            from src.ingestion.streamlit_app import main
            
            main()
            
            call_args = comprehensive_mocks['stats'].call_args[0][0]
            assert call_args["connection_type"] == "Cloud"
    
    def test_main_detects_cloud_connection(self, comprehensive_mocks):
        """Test that main detects cloud connection."""
        with patch.dict(os.environ, {"QDRANT_URL": "https://xyz.qdrant.io:6333"}):
            from src.ingestion.streamlit_app import main
            
            main()
            
            call_args = comprehensive_mocks['stats'].call_args[0][0]
            assert call_args["connection_type"] == "Cloud"
    
    def test_main_detects_cloud_when_no_qdrant_url_env(self, comprehensive_mocks):
        """Test connection type when QDRANT_URL env var is missing."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove QDRANT_URL if it exists
            os.environ.pop('QDRANT_URL', None)
            
            from src.ingestion.streamlit_app import main
            
            main()
            
            call_args = comprehensive_mocks['stats'].call_args[0][0]
            assert call_args["connection_type"] == "Cloud"


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestMainFunctionErrorHandling:
    """Test main function error handling."""
    
    def test_main_handles_qdrant_loader_initialization_error(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles QdrantLoader initialization errors."""
        comprehensive_mocks['loader_class'].side_effect = Exception(
            "Failed to connect to Qdrant"
        )
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        # Verify error was displayed (catches exception, doesn't raise)
        mock_streamlit.error.assert_called_once()
        error_msg = mock_streamlit.error.call_args[0][0]
        assert "Error initializing application" in error_msg
        
        mock_streamlit.exception.assert_called_once()
    
    def test_main_handles_get_collection_stats_error(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles get_collection_stats errors."""
        comprehensive_mocks['loader_instance'].get_collection_stats.side_effect = Exception(
            "Stats unavailable"
        )
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        mock_streamlit.error.assert_called_once()
        mock_streamlit.exception.assert_called_once()
    
    def test_main_handles_display_stats_error(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles display_collection_stats errors."""
        comprehensive_mocks['stats'].side_effect = Exception("Display failed")
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        mock_streamlit.error.assert_called_once()
    
    def test_main_handles_display_upload_section_error(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles display_upload_section errors."""
        comprehensive_mocks['upload'].side_effect = Exception("Upload UI failed")
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        mock_streamlit.error.assert_called_once()
    
    def test_main_handles_display_document_queue_error(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles display_document_queue errors."""
        comprehensive_mocks['queue'].side_effect = Exception("Queue display failed")
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        mock_streamlit.error.assert_called_once()


# ============================================================================
# TEST CLASS: Statistics Calculation
# ============================================================================


class TestMainStatisticsCalculation:
    """Test statistics calculation and formatting."""
    
    def test_main_calculates_total_chunks_correctly(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that total chunks from stats are correctly passed."""
        comprehensive_mocks['loader_instance'].get_collection_stats.return_value = {
            "total_documents": 250,
            "collection_name": "test",
            "embedding_model": "model",
            "provider": "Qdrant"
        }
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert call_args["total_chunks"] == 250
    
    def test_main_calculates_unique_documents_correctly(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that unique document count is correctly passed."""
        comprehensive_mocks['loader_instance'].get_unique_document_count.return_value = 25
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert call_args["unique_documents"] == 25
    
    def test_main_handles_zero_documents(self, comprehensive_mocks, mock_environment):
        """Test that main handles empty collection (zero documents)."""
        comprehensive_mocks['loader_instance'].get_collection_stats.return_value = {
            "total_documents": 0,
            "collection_name": "test",
            "embedding_model": "model",
            "provider": "Qdrant"
        }
        comprehensive_mocks['loader_instance'].get_unique_document_count.return_value = 0
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert call_args["total_chunks"] == 0
        assert call_args["unique_documents"] == 0


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""
    
    def test_complete_workflow_with_all_components(
        self, comprehensive_mocks, mock_environment
    ):
        """Test complete workflow from start to finish."""
        from src.ingestion.streamlit_app import main
        
        main()
        
        # Verify all components were called
        assert mock_streamlit.title.called
        assert mock_streamlit.markdown.called
        assert comprehensive_mocks['loader_instance'].get_collection_stats.called
        assert comprehensive_mocks['loader_instance'].get_unique_document_count.called
        assert comprehensive_mocks['stats'].called
        assert comprehensive_mocks['upload'].called
        assert comprehensive_mocks['queue'].called
    
    def test_workflow_with_large_collection(
        self, comprehensive_mocks, mock_environment
    ):
        """Test workflow with large collection."""
        comprehensive_mocks['loader_instance'].get_collection_stats.return_value = {
            "total_documents": 10000,
            "collection_name": "large_collection",
            "embedding_model": "model",
            "provider": "Qdrant"
        }
        comprehensive_mocks['loader_instance'].get_unique_document_count.return_value = 500
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert call_args["total_chunks"] == 10000
        assert call_args["unique_documents"] == 500


# ============================================================================
# TEST CLASS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_main_with_missing_stats_keys(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles missing keys in stats dict."""
        comprehensive_mocks['loader_instance'].get_collection_stats.return_value = {}
        
        from src.ingestion.streamlit_app import main
        
        # Should display error (doesn't raise, catches exception)
        main()
        
        mock_streamlit.error.assert_called_once()
    
    def test_main_with_none_stats_return(
        self, comprehensive_mocks, mock_environment
    ):
        """Test that main handles None return from get_collection_stats."""
        comprehensive_mocks['loader_instance'].get_collection_stats.return_value = None
        
        from src.ingestion.streamlit_app import main
        
        # Should display error
        main()
        
        mock_streamlit.error.assert_called_once()
    
    def test_main_with_negative_document_count(
        self, comprehensive_mocks, mock_environment
    ):
        """Test handling of negative document count (invalid state)."""
        comprehensive_mocks['loader_instance'].get_unique_document_count.return_value = -1
        
        from src.ingestion.streamlit_app import main
        
        main()
        
        call_args = comprehensive_mocks['stats'].call_args[0][0]
        assert call_args["unique_documents"] == -1


# ============================================================================
# NEW TEST CLASS: Page Configuration
# ============================================================================


class TestPageConfiguration:
    """Test page configuration separately."""
    
    def test_page_config_parameters(self, comprehensive_mocks):
        """Test that page config is called with correct parameters."""
        # Force a fresh import to trigger set_page_config
        if "src.ingestion.streamlit_app" in sys.modules:
            del sys.modules["src.ingestion.streamlit_app"]
        
        mock_streamlit.set_page_config.reset_mock()
        
        import src.ingestion.streamlit_app
        
        # Should be called at least once during import
        assert mock_streamlit.set_page_config.called
        
        # Check the most recent call
        call_kwargs = mock_streamlit.set_page_config.call_args[1]
        assert "page_title" in call_kwargs
        assert "page_icon" in call_kwargs
        assert "layout" in call_kwargs
        assert call_kwargs["initial_sidebar_state"] == "collapsed"


# ============================================================================
# NEW TEST CLASS: get_qdrant_loader Function
# ============================================================================


class TestGetQdrantLoader:
    """Test get_qdrant_loader caching function."""
    
    def test_get_qdrant_loader_returns_loader_instance(
        self, comprehensive_mocks
    ):
        """Test that get_qdrant_loader returns QdrantLoader instance."""
        from src.ingestion.streamlit_app import get_qdrant_loader
        
        result = get_qdrant_loader()
        
        comprehensive_mocks['loader_class'].assert_called()
        assert result == comprehensive_mocks['loader_instance']
    
    def test_get_qdrant_loader_handles_initialization_error(
        self, comprehensive_mocks
    ):
        """Test that get_qdrant_loader propagates initialization errors."""
        comprehensive_mocks['loader_class'].side_effect = Exception(
            "Failed to initialize Qdrant"
        )
        
        from src.ingestion.streamlit_app import get_qdrant_loader
        
        with pytest.raises(Exception, match="Failed to initialize Qdrant"):
            get_qdrant_loader()


# ============================================================================
# NEW TEST CLASS: Environment-Specific Tests
# ============================================================================


class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    def test_connection_type_with_various_localhost_formats(
        self, comprehensive_mocks
    ):
        """Test various localhost URL formats."""
        test_cases = [
            ("http://localhost:6333", "Local (Docker)"),
            ("https://localhost:6334", "Local (Docker)"),
            ("localhost:6333", "Local (Docker)"),
            ("http://127.0.0.1:6333", "Cloud"),
            ("https://example.qdrant.io", "Cloud"),
            ("", "Cloud"),
        ]
        
        for url, expected_type in test_cases:
            with patch.dict(os.environ, {"QDRANT_URL": url}):
                from src.ingestion.streamlit_app import main
                
                # Reset mocks
                comprehensive_mocks['stats'].reset_mock()
                
                main()
                
                call_args = comprehensive_mocks['stats'].call_args[0][0]
                assert call_args["connection_type"] == expected_type, \
                    f"Failed for URL: {url}"


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.ingestion.streamlit_app",
        "--cov-report=term-missing"
    ])