"""
Comprehensive unit tests for streamlit_stats.py

This test suite covers:
- display_collection_stats function with valid stats
- Error handling (error key in stats)
- Metric display verification
- Column layout verification
- Missing keys handling
- Edge cases (zero values, None values)
"""

import sys
from unittest.mock import MagicMock, patch, call

import pytest

# ============================================================================
# CRITICAL: Patch Streamlit BEFORE importing the module
# ============================================================================

mock_streamlit = MagicMock()
sys.modules['streamlit'] = mock_streamlit

# Mock all Streamlit components at the MODULE level (not column level)
mock_streamlit.markdown = MagicMock()
mock_streamlit.columns = MagicMock()
mock_streamlit.metric = MagicMock()
mock_streamlit.error = MagicMock()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_streamlit_mocks():
    """Reset all Streamlit mocks before each test."""
    mock_streamlit.markdown.reset_mock()
    mock_streamlit.columns.reset_mock()
    mock_streamlit.metric.reset_mock()
    mock_streamlit.error.reset_mock()
    yield


@pytest.fixture
def valid_stats():
    """Sample valid stats dictionary."""
    return {
        "unique_documents": 25,
        "total_chunks": 150,
        "connection_type": "Local (Docker)"
    }


@pytest.fixture
def stats_with_error():
    """Stats dictionary with error."""
    return {
        "error": "Connection timeout"
    }


@pytest.fixture
def setup_column_mocks():
    """
    Setup column mocks with proper context manager behavior.
    
    Key Learning: Mock at GLOBAL st level, not column level.
    The code uses 'with col1:', 'with col2:' which invokes context managers.
    """
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_col3 = MagicMock()
    
    # Setup context manager protocol
    mock_col1.__enter__ = MagicMock(return_value=mock_col1)
    mock_col1.__exit__ = MagicMock(return_value=False)
    mock_col2.__enter__ = MagicMock(return_value=mock_col2)
    mock_col2.__exit__ = MagicMock(return_value=False)
    mock_col3.__enter__ = MagicMock(return_value=mock_col3)
    mock_col3.__exit__ = MagicMock(return_value=False)
    
    # st.columns() returns these mocks
    mock_streamlit.columns.return_value = [mock_col1, mock_col2, mock_col3]
    
    return {
        'col1': mock_col1,
        'col2': mock_col2,
        'col3': mock_col3
    }


# ============================================================================
# TEST CLASS: Basic Functionality
# ============================================================================


class TestDisplayCollectionStatsBasics:
    """Test basic display_collection_stats functionality."""
    
    def test_displays_title_and_separators(self, valid_stats, setup_column_mocks):
        """Test that title and separator lines are displayed."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # Verify markdown calls
        markdown_calls = [call[0][0] for call in mock_streamlit.markdown.call_args_list]
        
        # Should have: title, separator before stats, separator after stats
        assert "Collection Statistics" in markdown_calls
        assert markdown_calls.count("---") >= 2
    
    def test_creates_three_columns(self, valid_stats, setup_column_mocks):
        """Test that three columns are created for metrics."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # Verify st.columns(3) was called
        mock_streamlit.columns.assert_called_once_with(3)
    
    def test_displays_all_three_metrics(self, valid_stats, setup_column_mocks):
        """Test that all three metrics are displayed."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # st.metric is called at the GLOBAL st level (not col.metric)
        # because the code uses 'with col:' context manager
        assert mock_streamlit.metric.call_count == 3
    
    def test_displays_unique_documents_metric(self, valid_stats, setup_column_mocks):
        """Test that unique documents metric is displayed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # Find the call with "Total Documents" label
        metric_calls = mock_streamlit.metric.call_args_list
        documents_call = None
        for call in metric_calls:
            if call[1].get('label') == "Total Documents":
                documents_call = call
                break
        
        assert documents_call is not None
        assert documents_call[1]['value'] == 25
        assert documents_call[1]['delta'] is None
    
    def test_displays_total_chunks_metric(self, valid_stats, setup_column_mocks):
        """Test that total chunks metric is displayed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # Find the call with "Total Chunks" label
        metric_calls = mock_streamlit.metric.call_args_list
        chunks_call = None
        for call in metric_calls:
            if call[1].get('label') == "Total Chunks":
                chunks_call = call
                break
        
        assert chunks_call is not None
        assert chunks_call[1]['value'] == 150
        assert chunks_call[1]['delta'] is None
    
    def test_displays_connection_type_metric(self, valid_stats, setup_column_mocks):
        """Test that connection type metric is displayed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # Find the call with "Connection" label
        metric_calls = mock_streamlit.metric.call_args_list
        connection_call = None
        for call in metric_calls:
            if call[1].get('label') == "Connection":
                connection_call = call
                break
        
        assert connection_call is not None
        assert connection_call[1]['value'] == "Local (Docker)"
        assert connection_call[1]['delta'] is None


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestDisplayCollectionStatsErrors:
    """Test error handling in display_collection_stats."""
    
    def test_displays_error_when_error_key_present(self, stats_with_error):
        """Test that error is displayed when 'error' key is in stats."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(stats_with_error)
        
        # Should display title and separator
        assert mock_streamlit.markdown.call_count >= 2
        
        # Should display error message
        mock_streamlit.error.assert_called_once()
        error_call = mock_streamlit.error.call_args[0][0]
        assert "Connection timeout" in error_call
    
    def test_returns_early_when_error_present(self, stats_with_error):
        """Test that function returns early when error is present."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(stats_with_error)
        
        # Should NOT create columns or display metrics
        mock_streamlit.columns.assert_not_called()
        mock_streamlit.metric.assert_not_called()
    
    def test_error_message_format(self, stats_with_error):
        """Test that error message is properly formatted."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(stats_with_error)
        
        error_call_args = mock_streamlit.error.call_args[0][0]
        assert "Error fetching statistics:" in error_call_args
        assert "Connection timeout" in error_call_args


# ============================================================================
# TEST CLASS: Edge Cases - Missing Keys
# ============================================================================


class TestDisplayCollectionStatsMissingKeys:
    """Test handling of missing keys in stats dictionary."""
    
    def test_handles_missing_unique_documents_key(self, setup_column_mocks):
        """Test that missing 'unique_documents' defaults to 0."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "total_chunks": 100,
            "connection_type": "Cloud"
            # Missing 'unique_documents'
        }
        
        display_collection_stats(stats)
        
        # Find the documents metric call
        metric_calls = mock_streamlit.metric.call_args_list
        documents_call = None
        for call in metric_calls:
            if call[1].get('label') == "Total Documents":
                documents_call = call
                break
        
        assert documents_call is not None
        assert documents_call[1]['value'] == 0
    
    def test_handles_missing_total_chunks_key(self, setup_column_mocks):
        """Test that missing 'total_chunks' defaults to 0."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 50,
            "connection_type": "Local"
            # Missing 'total_chunks'
        }
        
        display_collection_stats(stats)
        
        # Find the chunks metric call
        metric_calls = mock_streamlit.metric.call_args_list
        chunks_call = None
        for call in metric_calls:
            if call[1].get('label') == "Total Chunks":
                chunks_call = call
                break
        
        assert chunks_call is not None
        assert chunks_call[1]['value'] == 0
    
    def test_handles_missing_connection_type_key(self, setup_column_mocks):
        """Test that missing 'connection_type' defaults to 'Unknown'."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 25,
            "total_chunks": 150
            # Missing 'connection_type'
        }
        
        display_collection_stats(stats)
        
        # Find the connection metric call
        metric_calls = mock_streamlit.metric.call_args_list
        connection_call = None
        for call in metric_calls:
            if call[1].get('label') == "Connection":
                connection_call = call
                break
        
        assert connection_call is not None
        assert connection_call[1]['value'] == "Unknown"
    
    def test_handles_all_keys_missing(self, setup_column_mocks):
        """Test that empty stats dict uses all defaults."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {}
        
        display_collection_stats(stats)
        
        # Should still display all three metrics with defaults
        assert mock_streamlit.metric.call_count == 3
        
        # Verify default values
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        connection_call = next(c for c in metric_calls if c[1]['label'] == "Connection")
        
        assert documents_call[1]['value'] == 0
        assert chunks_call[1]['value'] == 0
        assert connection_call[1]['value'] == "Unknown"


# ============================================================================
# TEST CLASS: Edge Cases - Zero and Boundary Values
# ============================================================================


class TestDisplayCollectionStatsZeroValues:
    """Test handling of zero and boundary values."""
    
    def test_displays_zero_documents(self, setup_column_mocks):
        """Test that zero documents is displayed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 0,
            "total_chunks": 0,
            "connection_type": "Local"
        }
        
        display_collection_stats(stats)
        
        # Find the documents metric call
        metric_calls = mock_streamlit.metric.call_args_list
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        
        assert documents_call[1]['value'] == 0
    
    def test_displays_large_numbers(self, setup_column_mocks):
        """Test that large numbers are displayed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 1_000_000,
            "total_chunks": 50_000_000,
            "connection_type": "Cloud"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        
        assert documents_call[1]['value'] == 1_000_000
        assert chunks_call[1]['value'] == 50_000_000
    
    def test_displays_negative_numbers(self, setup_column_mocks):
        """Test that negative numbers (invalid state) are displayed."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": -1,
            "total_chunks": -5,
            "connection_type": "Error State"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        
        # Should display as-is (function doesn't validate)
        assert documents_call[1]['value'] == -1
        assert chunks_call[1]['value'] == -5


# ============================================================================
# TEST CLASS: Connection Type Variations
# ============================================================================


class TestDisplayCollectionStatsConnectionTypes:
    """Test various connection type displays."""
    
    def test_displays_local_docker_connection(self, setup_column_mocks):
        """Test displaying local Docker connection."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 10,
            "total_chunks": 50,
            "connection_type": "Local (Docker)"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        connection_call = next(c for c in metric_calls if c[1]['label'] == "Connection")
        
        assert connection_call[1]['value'] == "Local (Docker)"
    
    def test_displays_cloud_connection(self, setup_column_mocks):
        """Test displaying cloud connection."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 100,
            "total_chunks": 500,
            "connection_type": "Cloud"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        connection_call = next(c for c in metric_calls if c[1]['label'] == "Connection")
        
        assert connection_call[1]['value'] == "Cloud"
    
    def test_displays_custom_connection_string(self, setup_column_mocks):
        """Test displaying custom connection string."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 75,
            "total_chunks": 300,
            "connection_type": "Custom Server (192.168.1.100)"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        connection_call = next(c for c in metric_calls if c[1]['label'] == "Connection")
        
        assert connection_call[1]['value'] == "Custom Server (192.168.1.100)"


# ============================================================================
# TEST CLASS: Metric Properties
# ============================================================================


class TestDisplayCollectionStatsMetricProperties:
    """Test metric display properties."""
    
    def test_all_metrics_have_no_delta(self, valid_stats, setup_column_mocks):
        """Test that all metrics have delta=None."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # All metric calls should have delta=None
        metric_calls = mock_streamlit.metric.call_args_list
        
        for call in metric_calls:
            assert call[1]['delta'] is None
    
    def test_metrics_have_correct_labels(self, valid_stats, setup_column_mocks):
        """Test that metrics have correct labels."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        labels = [call[1]['label'] for call in metric_calls]
        
        assert "Total Documents" in labels
        assert "Total Chunks" in labels
        assert "Connection" in labels
    
    def test_metrics_called_in_correct_order(self, valid_stats, setup_column_mocks):
        """Test that metrics are called in the expected order."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        
        # Order: Total Documents, Total Chunks, Connection
        assert metric_calls[0][1]['label'] == "Total Documents"
        assert metric_calls[1][1]['label'] == "Total Chunks"
        assert metric_calls[2][1]['label'] == "Connection"


# ============================================================================
# TEST CLASS: Layout Verification
# ============================================================================


class TestDisplayCollectionStatsLayout:
    """Test layout and structure of display."""
    
    def test_markdown_calls_structure(self, valid_stats, setup_column_mocks):
        """Test the structure of markdown calls."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        markdown_calls = [call[0][0] for call in mock_streamlit.markdown.call_args_list]
        
        # Verify structure: title, separator, ..., separator
        assert markdown_calls[0] == "Collection Statistics"
        assert markdown_calls[1] == "---"
        assert markdown_calls[-1] == "---"
    
    def test_columns_created_before_metrics(self, valid_stats, setup_column_mocks):
        """Test that columns are created before metrics are displayed."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        # Create a list to track call order
        call_order = []
        
        def track_columns(*args, **kwargs):
            call_order.append('columns')
            return [
                setup_column_mocks['col1'],
                setup_column_mocks['col2'],
                setup_column_mocks['col3']
            ]
        
        def track_metric(*args, **kwargs):
            call_order.append('metric')
        
        mock_streamlit.columns.side_effect = track_columns
        mock_streamlit.metric.side_effect = track_metric
        
        display_collection_stats(valid_stats)
        
        # Columns should be called before any metrics
        assert call_order[0] == 'columns'
        assert call_order.count('metric') == 3
    
    def test_separators_placement(self, valid_stats, setup_column_mocks):
        """Test that separators are placed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        markdown_calls = [call[0][0] for call in mock_streamlit.markdown.call_args_list]
        
        # Should have separator after title
        title_index = markdown_calls.index("Collection Statistics")
        assert markdown_calls[title_index + 1] == "---"
        
        # Should have separator at the end
        assert markdown_calls[-1] == "---"


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestDisplayCollectionStatsIntegration:
    """Test complete integration scenarios."""
    
    def test_complete_display_workflow_with_valid_data(self, valid_stats, setup_column_mocks):
        """Test complete workflow with valid data."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(valid_stats)
        
        # Verify all components were called
        assert mock_streamlit.markdown.called
        assert mock_streamlit.columns.called
        assert mock_streamlit.metric.called
        assert not mock_streamlit.error.called
        
        # Verify correct number of calls
        assert mock_streamlit.markdown.call_count >= 3  # Title + 2 separators
        assert mock_streamlit.columns.call_count == 1
        assert mock_streamlit.metric.call_count == 3
    
    def test_complete_display_workflow_with_error(self, stats_with_error):
        """Test complete workflow when error is present."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        display_collection_stats(stats_with_error)
        
        # Verify error path
        assert mock_streamlit.markdown.called
        assert mock_streamlit.error.called
        assert not mock_streamlit.columns.called
        assert not mock_streamlit.metric.called
    
    def test_handles_mixed_valid_and_missing_keys(self, setup_column_mocks):
        """Test handling of partially filled stats dict."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 42,
            # Missing 'total_chunks'
            "connection_type": "Hybrid"
        }
        
        display_collection_stats(stats)
        
        # Should handle gracefully with defaults
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        connection_call = next(c for c in metric_calls if c[1]['label'] == "Connection")
        
        assert documents_call[1]['value'] == 42
        assert chunks_call[1]['value'] == 0  # Default
        assert connection_call[1]['value'] == "Hybrid"


# ============================================================================
# TEST CLASS: Type Handling
# ============================================================================


class TestDisplayCollectionStatsTypeHandling:
    """Test handling of various data types."""
    
    def test_handles_string_numbers(self, setup_column_mocks):
        """Test that string numbers are displayed as-is."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": "100",
            "total_chunks": "500",
            "connection_type": "Local"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        
        # Should display strings as-is (no conversion)
        assert documents_call[1]['value'] == "100"
        assert chunks_call[1]['value'] == "500"
    
    def test_handles_float_values(self, setup_column_mocks):
        """Test that float values are displayed correctly."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": 25.5,
            "total_chunks": 150.7,
            "connection_type": "Cloud"
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        
        assert documents_call[1]['value'] == 25.5
        assert chunks_call[1]['value'] == 150.7
    
    def test_handles_none_values_in_stats(self, setup_column_mocks):
        """Test that None values use defaults."""
        from src.ingestion.streamlit_stats import display_collection_stats
        
        stats = {
            "unique_documents": None,
            "total_chunks": None,
            "connection_type": None
        }
        
        display_collection_stats(stats)
        
        metric_calls = mock_streamlit.metric.call_args_list
        
        documents_call = next(c for c in metric_calls if c[1]['label'] == "Total Documents")
        chunks_call = next(c for c in metric_calls if c[1]['label'] == "Total Chunks")
        connection_call = next(c for c in metric_calls if c[1]['label'] == "Connection")
        
        # Should use defaults (get() with default value)
        assert documents_call[1]['value'] == 0, \
            "None value for unique_documents should default to 0"
        assert chunks_call[1]['value'] == 0, \
            "None value for total_chunks should default to 0"
        assert connection_call[1]['value'] == "Unknown", \
            "None value for connection_type should default to 'Unknown'"

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.ingestion.streamlit_stats",
        "--cov-report=term-missing"
    ])

