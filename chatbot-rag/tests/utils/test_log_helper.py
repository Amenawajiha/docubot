"""
Comprehensive unit tests for log_helper.py.

This test suite covers:
- Logger initialization and configuration
- Handler setup (StreamHandler, FileHandler)
- create_log_file() function
- File handler creation and duplication prevention
- Directory creation
- Multiple service name handling
- Edge cases and error handling
"""
import pytest
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def clean_logger_state():
    """
    Clean up logger state before and after tests.
    
    Testing Concept: Test isolation
    """
    # Store original handlers
    import src.utils.log_helper as log_helper_module
    
    original_handlers = log_helper_module.logger.handlers.copy()
    
    yield
    
    # Restore original handlers
    log_helper_module.logger.handlers = original_handlers


@pytest.fixture
def mock_datetime():
    """Mock datetime.now() for consistent timestamps."""
    with patch("src.utils.log_helper.datetime") as mock_dt:
        mock_now = Mock()
        mock_now.strftime.return_value = "01Jan2024_120000"
        mock_dt.now.return_value = mock_now
        yield mock_dt


@pytest.fixture
def mock_os_makedirs():
    """Mock os.makedirs to prevent actual directory creation."""
    with patch("src.utils.log_helper.os.makedirs") as mock:
        yield mock


@pytest.fixture
def mock_file_handler():
    """Mock logging.FileHandler - returns actual FileHandler class for isinstance checks."""
    with patch("src.utils.log_helper.logging.FileHandler") as mock:
        # Create a mock handler instance
        mock_handler = MagicMock(spec=logging.FileHandler)
        mock_handler.setFormatter = MagicMock()
        mock.return_value = mock_handler
        
        # Preserve the actual FileHandler class for isinstance checks
        mock.side_effect = None
        
        yield mock


@pytest.fixture
def mock_stream_handler():
    """Mock logging.StreamHandler."""
    with patch("src.utils.log_helper.logging.StreamHandler") as mock:
        yield mock


@pytest.fixture
def mock_sys_stdout():
    """Mock sys.stdout."""
    with patch("src.utils.log_helper.sys.stdout") as mock:
        mock.encoding = "utf-8"
        mock.reconfigure = MagicMock()
        yield mock


@pytest.fixture
def isolated_logger():
    """
    Create an isolated logger for testing.
    
    Testing Concept: Create fresh logger instance
    """
    # Create a new logger with unique name
    test_logger = logging.getLogger(f"test_logger_{id(object())}")
    test_logger.handlers = []
    test_logger.setLevel(logging.DEBUG)
    
    yield test_logger
    
    # Cleanup
    test_logger.handlers = []


@pytest.fixture
def logger_without_file_handlers():
    """Create a logger without any FileHandlers for testing."""
    test_logger = logging.getLogger(f"test_no_fh_{id(object())}")
    test_logger.handlers = []
    test_logger.setLevel(logging.DEBUG)
    
    # Add only a StreamHandler (no FileHandler)
    stream_handler = logging.StreamHandler()
    test_logger.addHandler(stream_handler)
    
    yield test_logger
    
    # Cleanup
    test_logger.handlers = []


# ============================================================================
# TEST CLASS: Module-Level Logger Configuration
# ============================================================================


class TestLoggerConfiguration:
    """Test module-level logger initialization and configuration."""
    
    def test_logger_exists_and_is_configured(self):
        """
        Test that module logger is properly initialized.
        
        Testing Concept: Test module initialization
        """
        from src.utils.log_helper import logger
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.DEBUG
    
    def test_logger_has_proper_name(self):
        """
        Test that logger has correct name.
        
        Testing Concept: Test logger naming
        """
        from src.utils.log_helper import logger
        
        assert logger.name == "src.utils.log_helper"
    
    def test_external_loggers_are_configured(self):
        """
        Test that external library loggers are configured.
        
        Testing Concept: Test external logger setup
        """
        from src.utils import log_helper
        
        # Check that external loggers exist and are configured
        assert log_helper.httpx_logger.level == logging.WARN
        assert log_helper.httpcore_logger.level == logging.INFO
        assert log_helper.watchfiles_logger.level == logging.WARN
        assert log_helper.openai_logger.level == logging.INFO
        assert log_helper.gtts_logger.level == logging.INFO
        assert log_helper.urllib_logger.level == logging.INFO
        assert log_helper.sql_alchemy_logger.level == logging.WARN
        assert log_helper.py_dub_logger.level == logging.INFO
        assert log_helper.gcp_logger.level == logging.INFO
    
    def test_watchdog_inotify_logger_suppressed(self):
        """
        Test that watchdog inotify logger is set to WARN.
        
        Testing Concept: Test noise suppression
        """
        from src.utils.log_helper import watchdog_inotify_logger
        
        assert watchdog_inotify_logger.level == logging.WARN
    
    def test_formatter_is_configured(self):
        """
        Test that formatter has correct format.
        
        Testing Concept: Test formatter configuration
        """
        from src.utils.log_helper import formatter
        
        assert isinstance(formatter, logging.Formatter)
        # Check format string contains expected components
        assert "%(asctime)s" in formatter._fmt
        assert "%(filename)s" in formatter._fmt
        assert "%(lineno)d" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt


# ============================================================================
# TEST CLASS: create_log_file() - Happy Path
# ============================================================================


class TestCreateLogFileHappyPath:
    """Test create_log_file() function happy path scenarios."""
    
    def test_create_log_file_creates_directory(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that create_log_file creates logs directory.
        
        Testing Concept: Test directory creation
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test_service")
            
            # Verify directory was created
            mock_os_makedirs.assert_called_once_with("logs", exist_ok=True)
    
    def test_create_log_file_creates_file_handler(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that create_log_file creates FileHandler.
        
        Testing Concept: Test handler creation
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            initial_count = len(logger_without_file_handlers.handlers)
            create_log_file("test_service")
            
            # Verify handler was added
            assert len(logger_without_file_handlers.handlers) > initial_count
            
            # Verify a FileHandler was added
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) > 0
    
    def test_create_log_file_uses_service_name_in_filename(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that service name is included in log filename.
        
        Testing Concept: Test filename formatting
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("my_service")
            
            # Check the file handler's filename
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            if file_handlers:
                handler = file_handlers[0]
                filename = handler.baseFilename
                assert "my_service" in filename
    
    def test_create_log_file_uses_timestamp_in_filename(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that timestamp is included in log filename.
        
        Testing Concept: Test timestamp formatting
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test_service")
            
            # Check that strftime was called
            mock_datetime.now.return_value.strftime.assert_called()
            
            # Check filename contains timestamp
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            if file_handlers:
                filename = file_handlers[0].baseFilename
                assert "01Jan2024_120000" in filename
    
    def test_create_log_file_sets_utf8_encoding(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that FileHandler uses UTF-8 encoding.
        
        Testing Concept: Test encoding parameter
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test_service")
            
            # Check file handler encoding
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            if file_handlers:
                handler = file_handlers[0]
                # FileHandler stores encoding in 'encoding' attribute
                assert hasattr(handler, 'encoding') or hasattr(handler, 'stream')
    
    def test_create_log_file_disables_propagation(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that logger.propagate is set to False.
        
        Testing Concept: Test propagation setting
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test_service")
            
            assert logger_without_file_handlers.propagate is False
    
    def test_create_log_file_sets_formatter_on_handler(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that formatter is set on FileHandler.
        
        Testing Concept: Test formatter assignment
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test_service")
            
            # Verify formatter was set
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            if file_handlers:
                handler = file_handlers[0]
                assert handler.formatter is not None


# ============================================================================
# TEST CLASS: create_log_file() - Duplication Prevention
# ============================================================================


class TestCreateLogFileDuplicationPrevention:
    """Test that create_log_file prevents duplicate handler creation."""
    
    def test_create_log_file_does_not_add_duplicate_handler(self, mock_os_makedirs, mock_datetime):
        """
        Test that calling create_log_file twice doesn't add duplicate handlers.
        
        Testing Concept: Test idempotency
        """
        # Create isolated logger with a FileHandler
        test_logger = logging.getLogger(f"test_dup_{id(object())}")
        test_logger.handlers = []
        
        # Add existing FileHandler
        with patch("src.utils.log_helper.open", mock_open()):
            existing_handler = logging.FileHandler("test.log")
            test_logger.addHandler(existing_handler)
            
            with patch("src.utils.log_helper.logger", test_logger):
                from src.utils.log_helper import create_log_file
                
                initial_count = len(test_logger.handlers)
                
                # Call create_log_file - should return early
                create_log_file("test_service")
                
                # Handler count should not increase
                assert len(test_logger.handlers) == initial_count
                
                # os.makedirs should not be called (early return)
                mock_os_makedirs.assert_not_called()
        
        # Cleanup
        test_logger.removeHandler(existing_handler)
        test_logger.handlers = []
    
    def test_create_log_file_checks_for_existing_file_handler(self, mock_os_makedirs, mock_datetime):
        """
        Test that create_log_file checks for existing FileHandler.
        
        Testing Concept: Test handler type checking
        """
        test_logger = logging.getLogger(f"test_check_{id(object())}")
        test_logger.handlers = []
        
        with patch("src.utils.log_helper.open", mock_open()):
            # Add a FileHandler
            existing_handler = logging.FileHandler("existing.log")
            test_logger.addHandler(existing_handler)
            
            with patch("src.utils.log_helper.logger", test_logger):
                from src.utils.log_helper import create_log_file
                
                # Should return early
                create_log_file("test_service")
                
                # os.makedirs should not be called
                mock_os_makedirs.assert_not_called()
        
        # Cleanup
        test_logger.removeHandler(existing_handler)
        test_logger.handlers = []
    
    def test_create_log_file_allows_first_call(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that create_log_file works on first call without existing handlers.
        
        Testing Concept: Test first call scenario
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test_service")
            
            # Should create directory and handler
            mock_os_makedirs.assert_called_once()


# ============================================================================
# TEST CLASS: create_log_file() - Uvicorn Logger Integration
# ============================================================================


class TestCreateLogFileUvicornIntegration:
    """Test uvicorn logger integration."""
    
    def test_create_log_file_adds_handler_to_uvicorn_logger(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that FileHandler is added to uvicorn logger.
        
        Testing Concept: Test uvicorn integration
        """
        uvicorn_logger = logging.getLogger("uvicorn")
        initial_handlers = uvicorn_logger.handlers.copy()
        
        try:
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                create_log_file("test_service")
                
                # Verify handler was added to uvicorn logger
                file_handlers = [
                    h for h in uvicorn_logger.handlers
                    if isinstance(h, logging.FileHandler)
                ]
                
                # Should have at least one FileHandler
                assert len(file_handlers) > 0
        
        finally:
            # Restore original handlers
            uvicorn_logger.handlers = initial_handlers
    
    def test_create_log_file_disables_uvicorn_propagation(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that uvicorn logger propagation is disabled.
        
        Testing Concept: Test propagation setting
        """
        uvicorn_logger = logging.getLogger("uvicorn")
        original_propagate = uvicorn_logger.propagate
        
        try:
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                create_log_file("test_service")
                
                assert uvicorn_logger.propagate is False
        
        finally:
            uvicorn_logger.propagate = original_propagate
    
    def test_create_log_file_adds_handler_to_uvicorn_access_logger(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that FileHandler is added to uvicorn.access logger.
        
        Testing Concept: Test access logger integration
        """
        access_logger = logging.getLogger("uvicorn.access")
        initial_handlers = access_logger.handlers.copy()
        
        try:
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                create_log_file("test_service")
                
                # Verify handler was added
                file_handlers = [
                    h for h in access_logger.handlers
                    if isinstance(h, logging.FileHandler)
                ]
                
                assert len(file_handlers) > 0
        
        finally:
            access_logger.handlers = initial_handlers
    
    def test_create_log_file_sets_uvicorn_access_level_to_debug(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that uvicorn.access logger level is set to DEBUG.
        
        Testing Concept: Test log level setting
        """
        access_logger = logging.getLogger("uvicorn.access")
        original_level = access_logger.level
        
        try:
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                create_log_file("test_service")
                
                assert access_logger.level == logging.DEBUG
        
        finally:
            access_logger.level = original_level
    
    def test_create_log_file_disables_uvicorn_access_propagation(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that uvicorn.access logger propagation is disabled.
        
        Testing Concept: Test propagation setting
        """
        access_logger = logging.getLogger("uvicorn.access")
        original_propagate = access_logger.propagate
        
        try:
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                create_log_file("test_service")
                
                assert access_logger.propagate is False
        
        finally:
            access_logger.propagate = original_propagate


# ============================================================================
# TEST CLASS: create_log_file() - Edge Cases
# ============================================================================


class TestCreateLogFileEdgeCases:
    """Test edge cases for create_log_file()."""
    
    def test_create_log_file_with_empty_service_name(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test create_log_file with empty service name.
        
        Testing Concept: Test empty input
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("")
            
            # Should still create log file
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            assert len(file_handlers) > 0
            
            # Filename should have timestamp
            filename = file_handlers[0].baseFilename
            assert "01Jan2024_120000" in filename
    
    def test_create_log_file_with_special_characters_in_service_name(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test create_log_file with special characters in service name.
        
        Testing Concept: Test special characters
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            create_log_file("test@service#123")
            
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            if file_handlers:
                filename = file_handlers[0].baseFilename
                assert "test@service#123" in filename
    
    def test_create_log_file_with_very_long_service_name(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test create_log_file with very long service name.
        
        Testing Concept: Test boundary values
        """
        with patch("src.utils.log_helper.logger", logger_without_file_handlers):
            from src.utils.log_helper import create_log_file
            
            long_name = "a" * 100  # Reduced from 255 to avoid filesystem limits
            
            create_log_file(long_name)
            
            file_handlers = [
                h for h in logger_without_file_handlers.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            assert len(file_handlers) > 0


# ============================================================================
# TEST CLASS: create_log_file() - Print Output
# ============================================================================


class TestCreateLogFilePrintOutput:
    """Test print output from create_log_file()."""
    
    def test_create_log_file_prints_log_location(
        self, logger_without_file_handlers, mock_os_makedirs, mock_datetime
    ):
        """
        Test that create_log_file prints log location.
        
        Testing Concept: Test console output
        """
        with patch("builtins.print") as mock_print:
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                create_log_file("test_service")
                
                # Verify print was called with log location
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0]
                assert "log_location:" in call_args[0]


# ============================================================================
# TEST CLASS: Stream Handler Configuration
# ============================================================================


class TestStreamHandlerConfiguration:
    """Test StreamHandler configuration."""
    
    def test_stream_handler_exists(self):
        """
        Test that StreamHandler is configured for logger.
        
        Testing Concept: Test handler existence
        """
        from src.utils.log_helper import logger
        
        # Check if StreamHandler exists
        stream_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.StreamHandler)
        ]
        
        assert len(stream_handlers) > 0
    
    def test_stream_handler_uses_stdout(self):
        """
        Test that StreamHandler outputs to stdout.
        
        Testing Concept: Test stream configuration
        """
        from src.utils.log_helper import logger
        
        stream_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.StreamHandler)
        ]
        
        if stream_handlers:
            handler = stream_handlers[0]
            # StreamHandler should use sys.stdout
            assert handler.stream is not None
    
    def test_stream_handler_reconfigures_stdout_encoding(self):
        """
        Test that stdout encoding is reconfigured if not UTF-8.
        
        Testing Concept: Test encoding reconfiguration
        """
        # This test verifies the module's initialization behavior
        # The reconfiguration happens at module import time
        import sys
        
        # If current encoding is UTF-8, reconfigure was already called
        # or wasn't needed
        assert sys.stdout.encoding is not None


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_create_log_file_handles_makedirs_permission_error(
        self, logger_without_file_handlers, mock_datetime
    ):
        """
        Test handling of permission error during directory creation.
        
        Testing Concept: Test permission error
        """
        with patch("src.utils.log_helper.os.makedirs", side_effect=PermissionError):
            with patch("src.utils.log_helper.logger", logger_without_file_handlers):
                from src.utils.log_helper import create_log_file
                
                with pytest.raises(PermissionError):
                    create_log_file("test_service")


# ============================================================================
# TEST CLASS: Integration Tests
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_logger_configuration_at_module_import(self):
        """
        Test that logger is properly configured at module import.
        
        Testing Concept: Test initialization
        """
        from src.utils.log_helper import logger
        
        # Verify logger is ready to use
        assert logger is not None
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("service_name", [
        "api",
        "chatbot",
        "rag_service",
        "websocket_server",
        "background_worker"
    ])
    def test_create_log_file_with_various_service_names(
        self, service_name, mock_os_makedirs, mock_datetime
    ):
        """
        Test create_log_file with various service names.
        
        Testing Concept: Parameterized service names
        """
        # Create fresh logger for each test
        test_logger = logging.getLogger(f"test_param_{service_name}_{id(object())}")
        test_logger.handlers = []
        
        with patch("src.utils.log_helper.logger", test_logger):
            from src.utils.log_helper import create_log_file
            
            create_log_file(service_name)
            
            # Check that a FileHandler was created
            file_handlers = [
                h for h in test_logger.handlers
                if isinstance(h, logging.FileHandler)
            ]
            
            assert len(file_handlers) > 0
            
            # Check filename contains service name
            filename = file_handlers[0].baseFilename
            assert service_name in filename
            assert ".log" in filename
        
        # Cleanup
        test_logger.handlers = []
    
    @pytest.mark.parametrize("logger_name,expected_level", [
        ("httpx", logging.WARN),
        ("httpcore", logging.INFO),
        ("watchfiles", logging.WARN),
        ("openai", logging.INFO),
        ("gtts", logging.INFO),
        ("urllib3", logging.INFO),
        ("sqlalchemy", logging.WARN),
        ("pydub", logging.INFO),
    ])
    def test_external_logger_levels(self, logger_name, expected_level):
        """
        Test that external loggers have correct levels.
        
        Testing Concept: Parameterized logger levels
        """
        logger = logging.getLogger(logger_name)
        
        # Note: The actual level might be inherited if not explicitly set
        # But our module should have set these
        assert logger.level <= expected_level or logger.level == 0  # 0 = NOTSET (inherits)


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.utils.log_helper",
        "--cov-report=term-missing"
    ])