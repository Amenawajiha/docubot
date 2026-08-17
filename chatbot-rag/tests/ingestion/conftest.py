"""
Test configuration for ingestion tests.

This file is executed BEFORE test collection, ensuring mocks are in place
before any test modules import the code under test.
"""

import sys
from unittest.mock import MagicMock
import pytest


@pytest.fixture(scope="function", autouse=False)
def mock_streamlit(monkeypatch):
    """
    Mock streamlit module.
    
    This fixture patches streamlit in sys.modules before the module
    under test imports it.
    """
    # Create mock streamlit
    mock_st = MagicMock()
    
    # Configure all streamlit functions
    mock_st.markdown = MagicMock()
    mock_st.file_uploader = MagicMock(return_value=None)
    mock_st.info = MagicMock()
    mock_st.button = MagicMock(return_value=False)
    mock_st.status = MagicMock()
    mock_st.error = MagicMock()
    mock_st.success = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.rerun = MagicMock()
    
    # Patch streamlit in sys.modules
    monkeypatch.setitem(sys.modules, "streamlit", mock_st)
    
    # If the module was already imported, reload it with the mock
    if "src.ingestion.streamlit_upload" in sys.modules:
        import importlib
        import src.ingestion.streamlit_upload
        importlib.reload(src.ingestion.streamlit_upload)
    
    yield mock_st


@pytest.fixture(autouse=True)
def reset_streamlit_mocks(mock_streamlit):
    """Reset all Streamlit mocks before each test."""
    mock_streamlit.markdown.reset_mock()
    mock_streamlit.file_uploader.reset_mock()
    mock_streamlit.info.reset_mock()
    mock_streamlit.button.reset_mock()
    mock_streamlit.status.reset_mock()
    mock_streamlit.error.reset_mock()
    mock_streamlit.success.reset_mock()
    mock_streamlit.warning.reset_mock()
    mock_streamlit.rerun.reset_mock()
    
    # Reset default return values
    mock_streamlit.file_uploader.return_value = None
    mock_streamlit.button.return_value = False
    
    yield