"""
Comprehensive unit tests for streamlit_doc_queue.py

This test suite covers:
- DocumentQueue initialization
- Log file parsing (success and failed entries)
- Document loading and sorting
- Document deletion (from Qdrant and log)
- Display functionality
- Document card rendering
- Error handling
- Edge cases (empty files, malformed entries, etc.)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open, call
from io import StringIO

import pytest

# ============================================================================
# CRITICAL: Patch Streamlit BEFORE importing the module
# ============================================================================

mock_streamlit = MagicMock()
sys.modules['streamlit'] = mock_streamlit

# Mock all Streamlit components
mock_streamlit.markdown = MagicMock()
mock_streamlit.checkbox = MagicMock()
mock_streamlit.info = MagicMock()
mock_streamlit.error = MagicMock()
mock_streamlit.success = MagicMock()
mock_streamlit.columns = MagicMock()
mock_streamlit.expander = MagicMock()
mock_streamlit.popover = MagicMock()
mock_streamlit.button = MagicMock()
mock_streamlit.spinner = MagicMock()
mock_streamlit.rerun = MagicMock()
mock_streamlit.code = MagicMock()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_streamlit_mocks():
    """Reset all Streamlit mocks before each test."""
    mock_streamlit.markdown.reset_mock()
    mock_streamlit.checkbox.reset_mock()
    mock_streamlit.info.reset_mock()
    mock_streamlit.error.reset_mock()
    mock_streamlit.success.reset_mock()
    mock_streamlit.columns.reset_mock()
    mock_streamlit.expander.reset_mock()
    mock_streamlit.popover.reset_mock()
    mock_streamlit.button.reset_mock()
    mock_streamlit.spinner.reset_mock()
    mock_streamlit.rerun.reset_mock()
    mock_streamlit.code.reset_mock()
    yield


@pytest.fixture
def mock_log_file(tmp_path):
    """Create a temporary log file for testing."""
    log_file = tmp_path / "upload_log.txt"
    return log_file


@pytest.fixture
def sample_log_content():
    """Sample log file content with various entry types."""
    return """[2024-01-15 10:30:00] SUCCESS: document1.pdf | Size: 1.2 MB
[2024-01-15 10:35:00] FAILED: document2.docx - Error: Invalid format
[2024-01-15 10:40:00] SUCCESS: document3.txt | Size: 500 KB
[2024-01-15 10:45:00] SUCCESS: document1.pdf | Size: 1.2 MB
[2024-01-15 10:50:00] FAILED: document4.xlsx - Error: Unsupported file type
"""


@pytest.fixture
def mock_qdrant_loader():
    """Mock QdrantLoader."""
    mock_loader = MagicMock()
    mock_loader.delete_document_chunks = MagicMock()
    return mock_loader


@pytest.fixture
def mock_config():
    """Mock configuration loader."""
    with patch("src.ingestion.streamlit_doc_queue.get_config") as mock:
        mock.return_value = "logs/upload_log.txt"
        yield mock


# ============================================================================
# TEST CLASS: Initialization
# ============================================================================


class TestDocumentQueueInitialization:
    """Test DocumentQueue initialization."""
    
    def test_init_with_explicit_log_file(self, mock_config):
        """Test initialization with explicit log file path."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        log_path = "custom/path/log.txt"
        queue = DocumentQueue(log_file=log_path)
        
        assert queue.log_file == Path(log_path)
        assert queue.qdrant_loader is None
        mock_config.assert_not_called()
    
    def test_init_with_default_log_file(self, mock_config):
        """Test initialization with config-based log file path."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        
        assert queue.log_file == Path("logs/upload_log.txt")
        mock_config.assert_called_once_with("upload.log_file")
    
    def test_init_with_qdrant_loader(self, mock_config, mock_qdrant_loader):
        """Test initialization with QdrantLoader instance."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue(qdrant_loader=mock_qdrant_loader)
        
        assert queue.qdrant_loader == mock_qdrant_loader
    
    def test_init_with_both_parameters(self, mock_config, mock_qdrant_loader):
        """Test initialization with both log file and loader."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        log_path = "custom/log.txt"
        queue = DocumentQueue(log_file=log_path, qdrant_loader=mock_qdrant_loader)
        
        assert queue.log_file == Path(log_path)
        assert queue.qdrant_loader == mock_qdrant_loader


# ============================================================================
# TEST CLASS: Log Line Parsing - Success Cases
# ============================================================================


class TestParseLogLineSuccess:
    """Test _parse_log_line for successful uploads."""
    
    def test_parse_success_with_size(self, mock_config):
        """Test parsing successful upload with file size."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] SUCCESS: document.pdf | Size: 1.2 MB"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['status'] == "success"
        assert result['filename'] == "document.pdf"
        assert result['file_size'] == "1.2 MB"
        assert result['timestamp'] == datetime(2024, 1, 15, 10, 30, 0)
        assert result['timestamp_str'] == "2024-01-15 10:30:00"
        assert result['error'] is None
    
    def test_parse_success_without_size(self, mock_config):
        """Test parsing successful upload without file size."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] SUCCESS: document.txt"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['status'] == "success"
        assert result['filename'] == "document.txt"
        assert result['file_size'] == "N/A"
        assert result['error'] is None
    
    def test_parse_success_with_special_characters_in_filename(self, mock_config):
        """Test parsing filename with special characters."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] SUCCESS: my-document_v2 (1).pdf | Size: 2.5 MB"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['filename'] == "my-document_v2 (1).pdf"
    
    def test_parse_success_with_spaces_in_filename(self, mock_config):
        """Test parsing filename with spaces."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] SUCCESS: My Document File.docx | Size: 800 KB"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['filename'] == "My Document File.docx"


# ============================================================================
# TEST CLASS: Log Line Parsing - Failed Cases
# ============================================================================


class TestParseLogLineFailed:
    """Test _parse_log_line for failed uploads."""
    
    def test_parse_failed_with_error_message(self, mock_config):
        """Test parsing failed upload with error message."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:35:00] FAILED: document.docx - Error: Invalid format"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['status'] == "failed"
        assert result['filename'] == "document.docx"
        assert result['file_size'] == "N/A"
        assert result['error'] == "Invalid format"
        assert result['timestamp'] == datetime(2024, 1, 15, 10, 35, 0)
    
    def test_parse_failed_without_error_message(self, mock_config):
        """Test parsing failed upload without error message."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:35:00] FAILED: document.xlsx"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['status'] == "failed"
        assert result['filename'] == "document.xlsx"
        assert result['error'] == "Unknown error"
    
    def test_parse_failed_with_complex_error_message(self, mock_config):
        """Test parsing failed upload with complex error message."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:35:00] FAILED: doc.pdf - Error: Connection timeout: Unable to reach server after 30s"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['status'] == "failed"
        assert result['error'] == "Connection timeout: Unable to reach server after 30s"


# ============================================================================
# TEST CLASS: Log Line Parsing - Edge Cases
# ============================================================================


class TestParseLogLineEdgeCases:
    """Test _parse_log_line edge cases and malformed input."""
    
    def test_parse_malformed_line_no_bracket(self, mock_config):
        """Test parsing line without timestamp brackets."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "2024-01-15 10:30:00 SUCCESS: document.pdf"
        
        result = queue._parse_log_line(line)
        
        assert result is None
    
    def test_parse_malformed_line_no_status(self, mock_config):
        """Test parsing line without SUCCESS/FAILED status."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] document.pdf"
        
        result = queue._parse_log_line(line)
        
        assert result is None
    
    def test_parse_empty_line(self, mock_config):
        """Test parsing empty line."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = ""
        
        result = queue._parse_log_line(line)
        
        assert result is None
    
    def test_parse_whitespace_only_line(self, mock_config):
        """Test parsing line with only whitespace."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "   \n"
        
        result = queue._parse_log_line(line)
        
        assert result is None
    
    def test_parse_invalid_timestamp_format(self, mock_config):
        """Test parsing line with invalid timestamp format."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024/01/15 10:30:00] SUCCESS: document.pdf"
        
        # Should handle exception and display error
        result = queue._parse_log_line(line)
        
        # Check that error was displayed
        assert mock_streamlit.error.called
    
    def test_parse_line_with_unicode_characters(self, mock_config):
        """Test parsing filename with unicode characters."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] SUCCESS: документ.pdf | Size: 1 MB"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        assert result['filename'] == "документ.pdf"
    
    def test_parse_line_with_multiple_pipes(self, mock_config):
        """Test parsing line with multiple pipe characters."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        line = "[2024-01-15 10:30:00] SUCCESS: file|name.pdf | Size: 1 MB"
        
        result = queue._parse_log_line(line)
        
        assert result is not None
        # Should handle the first pipe correctly
        assert "file|name.pdf" in result['filename']


# ============================================================================
# TEST CLASS: Load Documents
# ============================================================================


class TestLoadDocuments:
    """Test load_documents functionality."""
    
    def test_load_documents_from_existing_file(
        self, mock_config, mock_log_file, sample_log_content
    ):
        """Test loading documents from existing log file."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        # Write sample content to log file
        mock_log_file.write_text(sample_log_content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        documents = queue.load_documents()
        
        # Should return 4 unique documents (document1.pdf appears twice, keep latest)
        assert len(documents) == 4
        
        # Check newest first (LIFO order)
        assert documents[0]['filename'] == "document4.xlsx"
        assert documents[0]['status'] == "failed"
    
    def test_load_documents_from_nonexistent_file(self, mock_config):
        """Test loading from non-existent log file."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue(log_file="nonexistent.txt")
        documents = queue.load_documents()
        
        assert documents == []
    
    def test_load_documents_from_empty_file(self, mock_config, mock_log_file):
        """Test loading from empty log file."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text("")
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        documents = queue.load_documents()
        
        assert documents == []
    
    def test_load_documents_keeps_latest_entry_per_filename(
        self, mock_config, mock_log_file
    ):
        """Test that only the latest entry per filename is kept."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        # Multiple entries for same file
        content = """[2024-01-15 10:00:00] SUCCESS: doc.pdf | Size: 1 MB
[2024-01-15 11:00:00] SUCCESS: doc.pdf | Size: 1.1 MB
[2024-01-15 12:00:00] FAILED: doc.pdf - Error: Corrupted
"""
        mock_log_file.write_text(content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        documents = queue.load_documents()
        
        # Should keep only the latest entry (12:00:00, failed)
        assert len(documents) == 1
        assert documents[0]['status'] == "failed"
        assert documents[0]['timestamp_str'] == "2024-01-15 12:00:00"
    
    def test_load_documents_sorted_newest_first(
        self, mock_config, mock_log_file
    ):
        """Test that documents are sorted newest first."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        content = """[2024-01-15 10:00:00] SUCCESS: old.pdf | Size: 1 MB
[2024-01-15 15:00:00] SUCCESS: new.pdf | Size: 2 MB
[2024-01-15 12:00:00] SUCCESS: middle.pdf | Size: 1.5 MB
"""
        mock_log_file.write_text(content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        documents = queue.load_documents()
        
        assert len(documents) == 3
        assert documents[0]['filename'] == "new.pdf"
        assert documents[1]['filename'] == "middle.pdf"
        assert documents[2]['filename'] == "old.pdf"
    
    def test_load_documents_skips_malformed_lines(
        self, mock_config, mock_log_file
    ):
        """Test that malformed lines are skipped."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        content = """[2024-01-15 10:00:00] SUCCESS: good1.pdf | Size: 1 MB
malformed line without proper format
[2024-01-15 11:00:00] SUCCESS: good2.pdf | Size: 2 MB
another bad line
[2024-01-15 12:00:00] SUCCESS: good3.pdf | Size: 3 MB
"""
        mock_log_file.write_text(content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        documents = queue.load_documents()
        
        # Should only load 3 valid documents
        assert len(documents) == 3
        assert all(doc['filename'].startswith('good') for doc in documents)


# ============================================================================
# TEST CLASS: Remove from Log
# ============================================================================


class TestRemoveFromLog:
    """Test _remove_from_log functionality."""
    
    def test_remove_single_entry(self, mock_config, mock_log_file, sample_log_content):
        """Test removing a single document entry."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue._remove_from_log("document2.docx")
        
        # Verify entry was removed
        remaining_content = mock_log_file.read_text()
        assert "document2.docx" not in remaining_content
        assert "document1.pdf" in remaining_content
        assert "document3.txt" in remaining_content
    
    def test_remove_multiple_entries_same_filename(
        self, mock_config, mock_log_file
    ):
        """Test removing all entries for a filename that appears multiple times."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        content = """[2024-01-15 10:00:00] SUCCESS: doc.pdf | Size: 1 MB
[2024-01-15 11:00:00] SUCCESS: other.pdf | Size: 2 MB
[2024-01-15 12:00:00] SUCCESS: doc.pdf | Size: 1.1 MB
[2024-01-15 13:00:00] SUCCESS: doc.pdf | Size: 1.2 MB
"""
        mock_log_file.write_text(content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue._remove_from_log("doc.pdf")
        
        remaining_content = mock_log_file.read_text()
        
        # All doc.pdf entries should be removed
        assert "doc.pdf" not in remaining_content
        # Other entries should remain
        assert "other.pdf" in remaining_content
    
    def test_remove_from_nonexistent_file(self, mock_config):
        """Test removing from non-existent log file."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue(log_file="nonexistent.txt")
        
        # Should not raise error
        queue._remove_from_log("document.pdf")
    
    def test_remove_nonexistent_filename(
        self, mock_config, mock_log_file, sample_log_content
    ):
        """Test removing a filename that doesn't exist in log."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        original_content = sample_log_content
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue._remove_from_log("nonexistent.pdf")
        
        # Content should remain unchanged
        assert mock_log_file.read_text() == original_content
    
    def test_remove_preserves_other_entries(
        self, mock_config, mock_log_file, sample_log_content
    ):
        """Test that removing one entry preserves others."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        
        # Count lines before
        lines_before = len(mock_log_file.read_text().strip().split('\n'))
        
        queue._remove_from_log("document3.txt")
        
        # Should have one less line
        lines_after = len(mock_log_file.read_text().strip().split('\n'))
        assert lines_after == lines_before - 1
    
    def test_remove_with_malformed_lines_in_log(
        self, mock_config, mock_log_file
    ):
        """Test removing from log with malformed lines."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        content = """[2024-01-15 10:00:00] SUCCESS: good.pdf | Size: 1 MB
malformed line 1
[2024-01-15 11:00:00] SUCCESS: target.pdf | Size: 2 MB
malformed line 2
[2024-01-15 12:00:00] SUCCESS: other.pdf | Size: 3 MB
"""
        mock_log_file.write_text(content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue._remove_from_log("target.pdf")
        
        remaining_content = mock_log_file.read_text()
        
        # Target should be removed
        assert "target.pdf" not in remaining_content
        # Malformed lines should be preserved
        assert "malformed line 1" in remaining_content
        assert "malformed line 2" in remaining_content


# ============================================================================
# TEST CLASS: Delete Document
# ============================================================================


class TestDeleteDocument:
    """Test delete_document functionality."""
    
    def test_delete_document_with_qdrant_loader(
        self, mock_config, mock_log_file, mock_qdrant_loader, sample_log_content
    ):
        """Test deleting document with QdrantLoader available."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        queue = DocumentQueue(
            log_file=str(mock_log_file),
            qdrant_loader=mock_qdrant_loader
        )
        
        success = queue.delete_document("document1.pdf")
        
        assert success is True
        mock_qdrant_loader.delete_document_chunks.assert_called_once_with("document1.pdf")
        
        # Verify removed from log
        remaining_content = mock_log_file.read_text()
        assert "document1.pdf" not in remaining_content
    
    def test_delete_document_without_qdrant_loader(
        self, mock_config, mock_log_file, sample_log_content
    ):
        """Test deleting document without QdrantLoader."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        
        success = queue.delete_document("document2.docx")
        
        assert success is True
        
        # Should still remove from log
        remaining_content = mock_log_file.read_text()
        assert "document2.docx" not in remaining_content
    
    def test_delete_document_handles_qdrant_error(
        self, mock_config, mock_log_file, mock_qdrant_loader, sample_log_content
    ):
        """Test that delete handles Qdrant deletion errors."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        # Make Qdrant deletion fail
        mock_qdrant_loader.delete_document_chunks.side_effect = Exception(
            "Qdrant connection error"
        )
        
        queue = DocumentQueue(
            log_file=str(mock_log_file),
            qdrant_loader=mock_qdrant_loader
        )
        
        success = queue.delete_document("document1.pdf")
        
        assert success is False
        mock_streamlit.error.assert_called_once()
    
    def test_delete_document_handles_log_removal_error(
        self, mock_config, mock_qdrant_loader
    ):
        """Test that delete handles log removal errors."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue(
            log_file="readonly.txt",
            qdrant_loader=mock_qdrant_loader
        )
        
        # Mock file operations to raise error
        with patch.object(Path, 'exists', return_value=True):
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                success = queue.delete_document("document.pdf")
                
                assert success is False
                mock_streamlit.error.assert_called_once()


# ============================================================================
# TEST CLASS: Display Functionality
# ============================================================================


class TestDisplayFunctionality:
    """Test display method."""
    
    def test_display_with_checkbox_unchecked(
        self, mock_config, mock_log_file, sample_log_content
    ):
        """Test display when checkbox is unchecked."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        # Mock checkbox to return False
        mock_streamlit.checkbox.return_value = False
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue.display()
        
        # Should show checkbox
        mock_streamlit.checkbox.assert_called_once()
        
        # Should not show document list
        assert not mock_streamlit.info.called
    
    def test_display_with_checkbox_checked_no_documents(self, mock_config, mock_log_file):
        """Test display when checkbox is checked but no documents exist."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text("")
        
        mock_streamlit.checkbox.return_value = True
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue.display()
        
        # Should show info message
        mock_streamlit.info.assert_called_once_with("No documents uploaded yet.")
    
    def test_display_with_checkbox_checked_with_documents(
        self, mock_config, mock_log_file, sample_log_content
    ):
        """Test display when checkbox is checked with documents."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_log_file.write_text(sample_log_content)
        
        mock_streamlit.checkbox.return_value = True
        
        # Mock columns and expander
        mock_col = MagicMock()
        mock_streamlit.columns.return_value = [mock_col, mock_col]
        mock_streamlit.expander.return_value.__enter__ = MagicMock()
        mock_streamlit.expander.return_value.__exit__ = MagicMock()
        mock_streamlit.popover.return_value.__enter__ = MagicMock()
        mock_streamlit.popover.return_value.__exit__ = MagicMock()
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue.display()
        
        # Should show document count
        markdown_calls = [str(call) for call in mock_streamlit.markdown.call_args_list]
        assert any("4 documents" in str(call) for call in markdown_calls)
    
    def test_display_shows_separator(self, mock_config):
        """Test that display shows separator line."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        mock_streamlit.checkbox.return_value = False
        
        queue = DocumentQueue()
        queue.display()
        
        # Check first markdown call is separator
        first_call = mock_streamlit.markdown.call_args_list[0]
        assert "---" in str(first_call)


# ============================================================================
# TEST CLASS: Display Document Card 
# ============================================================================


class TestDisplayDocumentCard:
    """Test _display_document_card method."""
    
    def test_display_document_card_success(self, mock_config):
        """Test displaying a successful document card."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'test.pdf',
            'status': 'success',
            'timestamp_str': '2024-01-15 10:30:00',
            'file_size': '1.2 MB',
            'error': None
        }
        
        # Mock the columns context managers
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        
        # Mock context manager behavior
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        
        # Mock expander context manager
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        # Mock popover context manager
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        # Mock columns inside expander
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        
        # Make expander.columns return these mocks
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])
        
        # Mock button to return False (not clicked)
        mock_streamlit.button.return_value = False
        
        queue = DocumentQueue()
        queue._display_document_card(doc, position=1)
        
        # Verify expander was called with success icon
        mock_streamlit.expander.assert_called_once()
        expander_call = mock_streamlit.expander.call_args
        assert "✅" in expander_call[0][0]
        assert "test.pdf" in expander_call[0][0]
        assert expander_call[1]['expanded'] is True
    
    def test_display_document_card_failed(self, mock_config):
        """Test displaying a failed document card."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'failed.docx',
            'status': 'failed',
            'timestamp_str': '2024-01-15 11:00:00',
            'file_size': 'N/A',
            'error': 'Invalid format'
        }
        
        # Setup mocks
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])
        
        mock_streamlit.button.return_value = False
        
        queue = DocumentQueue()
        queue._display_document_card(doc, position=2)

        # Verify expander was called with failed icon
        expander_call = mock_streamlit.expander.call_args
        assert expander_call is not None
        assert "❌" in expander_call[0][0]
        assert "failed.docx" in expander_call[0][0]

    def test_display_document_card_first_position_expanded(self, mock_config):
        """Test that first document is expanded by default."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'first.pdf',
            'status': 'success',
            'timestamp_str': '2024-01-15 10:30:00',
            'file_size': '1 MB',
            'error': None
        }
        
        # Setup mocks
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])
        
        mock_streamlit.button.return_value = False
        
        queue = DocumentQueue()
        queue._display_document_card(doc, position=1)

        # Verify expanded=True for position 1
        expander_kwargs = mock_streamlit.expander.call_args[1]
        assert expander_kwargs['expanded'] is True
    
    def test_display_document_card_not_first_position_collapsed(self, mock_config):
        """Test that non-first documents are collapsed."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'second.pdf',
            'status': 'success',
            'timestamp_str': '2024-01-15 10:30:00',
            'file_size': '1 MB',
            'error': None
        }
        
        # Setup mocks
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])
        
        mock_streamlit.button.return_value = False
        
        queue = DocumentQueue()
        queue._display_document_card(doc, position=2)
        # Verify expanded=False for position > 1
        expander_kwargs = mock_streamlit.expander.call_args[1]
        assert expander_kwargs['expanded'] is False
    
    def test_display_document_card_shows_error_for_failed(self, mock_config):
        """Test that error details are displayed for failed documents."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'error.pdf',
            'status': 'failed',
            'timestamp_str': '2024-01-15 10:30:00',
            'file_size': 'N/A',
            'error': 'Connection timeout'
        }
        
        # Setup mocks
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])

        mock_streamlit.button.return_value = False
        
        queue = DocumentQueue()
        queue._display_document_card(doc, position=1)
        
        # Verify st.code was called with error message
        mock_streamlit.code.assert_called_once_with('Connection timeout', language=None)
    
    def test_display_document_card_delete_button_not_clicked(self, mock_config):
        """Test that nothing happens when delete button is not clicked."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'test.pdf',
            'status': 'success',
            'timestamp_str': '2024-01-15 10:30:00',
            'file_size': '1 MB',
            'error': None
        }
        
        # Setup mocks
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])
        
        # Button returns False (not clicked)
        mock_streamlit.button.return_value = False
        
        queue = DocumentQueue()
        queue._display_document_card(doc, position=1)
        
        # Verify button was called
        mock_streamlit.button.assert_called_once()
        
        # Verify no delete operations were triggered
        assert not mock_streamlit.success.called
        assert not mock_streamlit.rerun.called
    
    def test_display_document_card_delete_button_clicked(self, mock_config, mock_qdrant_loader):
        """Test delete workflow when button is clicked."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        doc = {
            'filename': 'delete_me.pdf',
            'status': 'success',
            'timestamp_str': '2024-01-15 10:30:00',
            'file_size': '1 MB',
            'error': None
        }
        
        # Setup mocks
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_streamlit.columns.return_value = [mock_col1, mock_col2]
        
        mock_col1.__enter__ = MagicMock(return_value=mock_col1)
        mock_col1.__exit__ = MagicMock(return_value=False)
        mock_col2.__enter__ = MagicMock(return_value=mock_col2)
        mock_col2.__exit__ = MagicMock(return_value=False)
        
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_streamlit.expander.return_value = mock_expander
        
        mock_popover = MagicMock()
        mock_popover.__enter__ = MagicMock(return_value=mock_popover)
        mock_popover.__exit__ = MagicMock(return_value=False)
        mock_streamlit.popover.return_value = mock_popover
        
        mock_info_col1 = MagicMock()
        mock_info_col2 = MagicMock()
        mock_info_col1.__enter__ = MagicMock(return_value=mock_info_col1)
        mock_info_col1.__exit__ = MagicMock(return_value=False)
        mock_info_col2.__enter__ = MagicMock(return_value=mock_info_col2)
        mock_info_col2.__exit__ = MagicMock(return_value=False)
        mock_expander.columns = MagicMock(return_value=[mock_info_col1, mock_info_col2])
        
        # Button returns True (clicked)
        mock_streamlit.button.return_value = True
        
        # Mock spinner context manager
        mock_spinner = MagicMock()
        mock_spinner.__enter__ = MagicMock(return_value=mock_spinner)
        mock_spinner.__exit__ = MagicMock(return_value=False)
        mock_streamlit.spinner.return_value = mock_spinner

        # Create queue with qdrant loader
        queue = DocumentQueue(qdrant_loader=mock_qdrant_loader)
        
        # Mock the delete to succeed
        with patch.object(queue, 'delete_document', return_value=True):
            queue._display_document_card(doc, position=1)
            
            # Verify delete was called
            queue.delete_document.assert_called_once_with('delete_me.pdf')
            
            # Verify success message and rerun
            mock_streamlit.success.assert_called_once()
            mock_streamlit.rerun.assert_called_once()


# ============================================================================
# TEST CLASS: Display Document Queue Function
# ============================================================================


class TestDisplayDocumentQueueFunction:
    """Test the module-level display_document_queue function."""
    
    def test_display_document_queue_without_loader(self, mock_config):
        """Test display_document_queue function without loader."""
        from src.ingestion.streamlit_doc_queue import display_document_queue
        
        mock_streamlit.checkbox.return_value = False
        
        display_document_queue()
        
        # Should create queue and display
        mock_streamlit.checkbox.assert_called_once()
    
    def test_display_document_queue_with_loader(
        self, mock_config, mock_qdrant_loader
    ):
        """Test display_document_queue function with loader."""
        from src.ingestion.streamlit_doc_queue import display_document_queue
        
        mock_streamlit.checkbox.return_value = False
        
        display_document_queue(qdrant_loader=mock_qdrant_loader)
        
        mock_streamlit.checkbox.assert_called_once()


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestIntegrationScenarios:
    """Test complete workflow scenarios."""
    
    def test_complete_delete_workflow(
        self, mock_config, mock_log_file, mock_qdrant_loader
    ):
        """Test complete delete workflow from button click to rerun."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        content = """[2024-01-15 10:00:00] SUCCESS: delete_me.pdf | Size: 1 MB
[2024-01-15 11:00:00] SUCCESS: keep_me.pdf | Size: 2 MB
"""
        mock_log_file.write_text(content)
        
        queue = DocumentQueue(
            log_file=str(mock_log_file),
            qdrant_loader=mock_qdrant_loader
        )
        
        # Delete document
        success = queue.delete_document("delete_me.pdf")
        
        assert success is True
        
        # Verify Qdrant deletion
        mock_qdrant_loader.delete_document_chunks.assert_called_once_with("delete_me.pdf")
        
        # Verify log update
        remaining_content = mock_log_file.read_text()
        assert "delete_me.pdf" not in remaining_content
        assert "keep_me.pdf" in remaining_content
        
        # Verify document list updated
        documents = queue.load_documents()
        assert len(documents) == 1
        assert documents[0]['filename'] == "keep_me.pdf"
    
    def test_workflow_with_mixed_statuses(
        self, mock_config, mock_log_file
    ):
        """Test workflow with mix of success and failed documents."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        content = """[2024-01-15 10:00:00] SUCCESS: good1.pdf | Size: 1 MB
[2024-01-15 11:00:00] FAILED: bad1.docx - Error: Invalid
[2024-01-15 12:00:00] SUCCESS: good2.txt | Size: 500 KB
[2024-01-15 13:00:00] FAILED: bad2.xlsx - Error: Unsupported
"""
        mock_log_file.write_text(content)
        
        mock_streamlit.checkbox.return_value = True
        
        # Setup mocks for display
        mock_col_expand = MagicMock()
        mock_col_menu = MagicMock()
        mock_streamlit.columns.return_value = [mock_col_expand, mock_col_menu]
        
        mock_expander_context = MagicMock()
        mock_col_expand.expander.return_value = mock_expander_context
        mock_expander_context.__enter__ = MagicMock()
        mock_expander_context.__exit__ = MagicMock()
        
        mock_popover_context = MagicMock()
        mock_col_menu.popover.return_value = mock_popover_context
        mock_popover_context.__enter__ = MagicMock()
        mock_popover_context.__exit__ = MagicMock()
        
        queue = DocumentQueue(log_file=str(mock_log_file))
        queue.display()
        
        # Should show all 4 documents
        markdown_calls = [str(call) for call in mock_streamlit.markdown.call_args_list]
        assert any("4 documents" in str(call) for call in markdown_calls)


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling across various scenarios."""
    
    def test_parse_handles_unicode_decode_error(self, mock_config):
        """Test parsing handles unicode decode errors gracefully."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue()
        
        # Line with problematic characters that could cause decode issues
        line = "[2024-01-15 10:30:00] SUCCESS: \xFF\xFE.pdf | Size: 1 MB"
        
        # Should handle gracefully
        result = queue._parse_log_line(line)
        
        # Either returns result or None, but shouldn't crash
        assert result is None or isinstance(result, dict)
    
    def test_load_handles_file_read_error(self, mock_config):
        """Test load_documents handles file read errors."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        queue = DocumentQueue(log_file="/invalid/path/log.txt")
        
        # Should return empty list, not crash
        documents = queue.load_documents()
        assert documents == []
    
    def test_delete_handles_all_exceptions(
        self, mock_config, mock_qdrant_loader
    ):
        """Test that delete_document catches and handles all exceptions."""
        from src.ingestion.streamlit_doc_queue import DocumentQueue
        
        # Make both Qdrant and log removal fail
        mock_qdrant_loader.delete_document_chunks.side_effect = Exception("Qdrant error")
        
        queue = DocumentQueue(
            log_file="/invalid/path.txt",
            qdrant_loader=mock_qdrant_loader
        )
        
        success = queue.delete_document("doc.pdf")
        
        assert success is False
        mock_streamlit.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.ingestion.streamlit_doc_queue",
        "--cov-report=term-missing"
    ])

