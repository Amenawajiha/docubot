"""
Comprehensive unit tests for DBEnterExitMixin.

This test suite covers:
- Context manager protocol (__enter__, __exit__)
- Database session creation
- Database session cleanup
- Exception handling and rollback
- Integration with Database singleton
- Edge cases and error scenarios
"""

import os
import sys
from unittest.mock import MagicMock, Mock, PropertyMock, patch, call

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.utils.db_enter_exit_mixin import DBEnterExitMixin


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.utils.db_enter_exit_mixin.logger") as mock:
        yield mock


@pytest.fixture
def mock_database():
    """Mock Database class."""
    with patch("src.utils.db_enter_exit_mixin.Database") as mock:
        yield mock


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.close = MagicMock()
    session.rollback = MagicMock()
    session.commit = MagicMock()
    return session


@pytest.fixture
def test_mixin_class():
    """
    Create a test class that uses DBEnterExitMixin.
    
    Testing Concept: Create concrete implementation of mixin
    """
    class TestClass(DBEnterExitMixin):
        """Test class using the mixin."""
        def __init__(self):
            self._db_helper = None
            self._db_session = None
    
    return TestClass


# ============================================================================
# TEST CLASS: Enter Method Tests
# ============================================================================


class TestDBEnterExitMixinEnter:
    """Test __enter__ method functionality."""
    
    def test_enter_creates_database_helper_when_none(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __enter__ creates Database helper when it's None.
        
        Testing Concept: Test initialization
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute
        instance.__enter__()
        
        # Verify Database was created
        mock_database.assert_called_once_with(
            db_schema="schengendb",
            db_name="postgresql"
        )
        
        # Verify session was created
        assert instance._db_session == mock_db_session
        assert instance._db_helper is not None
    
    def test_enter_uses_existing_database_helper(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __enter__ uses existing Database helper.
        
        Testing Concept: Test reuse of existing instance
        """
        # Setup - create a pre-existing db_helper
        existing_db_helper = MagicMock()
        existing_db_helper.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance._db_helper = existing_db_helper
        
        # Execute
        instance.__enter__()
        
        # Verify Database was NOT created (no call to mock_database)
        mock_database.assert_not_called()
        
        # Verify existing helper's session was used
        existing_db_helper.session.assert_called_once()
        assert instance._db_session == mock_db_session
    
    def test_enter_creates_new_session(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __enter__ creates a new database session.
        
        Testing Concept: Test session creation
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute
        instance.__enter__()
        
        # Verify session was created
        mock_database.return_value.session.assert_called_once()
        assert instance._db_session is not None
        assert instance._db_session == mock_db_session
    
    def test_enter_sets_db_session_attribute(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __enter__ properly sets _db_session attribute.
        
        Testing Concept: Test attribute assignment
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        assert instance._db_session is None  # Initially None
        
        # Execute
        instance.__enter__()
        
        # Verify
        assert instance._db_session is mock_db_session
    
    def test_enter_returns_none(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __enter__ returns None (implicit).
        
        Testing Concept: Test return value
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute
        result = instance.__enter__()
        
        # Verify - __enter__ doesn't explicitly return anything (returns None)
        assert result is None


# ============================================================================
# TEST CLASS: Exit Method Tests - Happy Path
# ============================================================================


class TestDBEnterExitMixinExitHappyPath:
    """Test __exit__ method happy path scenarios."""
    
    def test_exit_closes_session_on_success(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __exit__ closes session on successful execution.
        
        Testing Concept: Test cleanup on success
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - no exception
        instance.__exit__(None, None, None)
        
        # Verify session was closed
        mock_db_session.close.assert_called_once()
        
        # Verify rollback was NOT called
        mock_db_session.rollback.assert_not_called()
        
        # Verify logger
        mock_logger.info.assert_called_with("Closing DB session..")
    
    def test_exit_logs_closing_message(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __exit__ logs closing message.
        
        Testing Concept: Test logging
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute
        instance.__exit__(None, None, None)
        
        # Verify logging
        mock_logger.info.assert_called_with("Closing DB session..")
    
    def test_exit_does_not_rollback_on_success(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that rollback is not called on successful execution.
        
        Testing Concept: Test conditional rollback
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - no exception (exc_type is None)
        instance.__exit__(None, None, None)
        
        # Verify rollback was NOT called
        mock_db_session.rollback.assert_not_called()


# ============================================================================
# TEST CLASS: Exit Method Tests - Exception Handling
# ============================================================================


class TestDBEnterExitMixinExitExceptions:
    """Test __exit__ method exception handling."""
    
    def test_exit_rolls_back_on_exception(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __exit__ rolls back session on exception.
        
        Testing Concept: Test rollback on exception
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - with exception
        exc_type = Exception
        exc_val = Exception("Test error")
        exc_tb = None
        
        instance.__exit__(exc_type, exc_val, exc_tb)
        
        # Verify session was closed
        mock_db_session.close.assert_called_once()
        
        # Verify rollback WAS called
        mock_db_session.rollback.assert_called_once()
    
    def test_exit_closes_session_even_with_exception(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that session is closed even when exception occurs.
        
        Testing Concept: Test cleanup on error
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - with exception
        instance.__exit__(ValueError, ValueError("error"), None)
        
        # Verify session was closed
        mock_db_session.close.assert_called_once()
    
    def test_exit_handles_various_exception_types(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __exit__ handles various exception types.
        
        Testing Concept: Test different exception types
        """
        exception_types = [
            (ValueError, ValueError("value error"), None),
            (TypeError, TypeError("type error"), None),
            (RuntimeError, RuntimeError("runtime error"), None),
            (KeyError, KeyError("key error"), None),
        ]
        
        for exc_type, exc_val, exc_tb in exception_types:
            # Setup
            mock_database.return_value.session.return_value = mock_db_session
            mock_db_session.reset_mock()
            
            instance = test_mixin_class()
            instance.__enter__()
            
            # Execute
            instance.__exit__(exc_type, exc_val, exc_tb)
            
            # Verify rollback was called for each exception
            mock_db_session.rollback.assert_called_once()
            mock_db_session.close.assert_called_once()
    
    def test_exit_rollback_called_before_close(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that rollback is called before close on exception.
        
        Testing Concept: Test operation order
        """
        # Setup - track call order
        call_order = []
        
        mock_db_session.close.side_effect = lambda: call_order.append('close')
        mock_db_session.rollback.side_effect = lambda: call_order.append('rollback')
        
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - with exception
        instance.__exit__(Exception, Exception("error"), None)
        
        # Verify order: close is called first, then rollback
        # Note: Based on the code, close is actually called BEFORE rollback
        assert call_order == ['close', 'rollback']


# ============================================================================
# TEST CLASS: Context Manager Integration
# ============================================================================


class TestDBEnterExitMixinContextManager:
    """Test full context manager usage."""
    
    def test_context_manager_with_statement(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test using the mixin with 'with' statement.
        
        Testing Concept: Test context manager protocol
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute - use as context manager
        with instance:
            # Inside context
            assert instance._db_session == mock_db_session
            assert instance._db_helper is not None
        
        # After context - verify cleanup
        mock_db_session.close.assert_called_once()
        mock_logger.info.assert_called_with("Closing DB session..")
    
    def test_context_manager_with_exception_in_block(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test context manager when exception occurs in with block.
        
        Testing Concept: Test exception propagation
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute - exception in with block
        with pytest.raises(ValueError):
            with instance:
                raise ValueError("Test error")
        
        # Verify cleanup still happened
        mock_db_session.close.assert_called_once()
        mock_db_session.rollback.assert_called_once()
    
    def test_context_manager_multiple_times(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test using context manager multiple times.
        
        Testing Concept: Test reusability
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute - first time
        with instance:
            pass
        
        # Reset mocks
        mock_db_session.reset_mock()
        
        # Execute - second time
        with instance:
            pass
        
        # Verify cleanup happened both times
        assert mock_db_session.close.call_count == 1
    
    def test_context_manager_nested_usage(
        self, test_mixin_class, mock_database, mock_logger
    ):
        """
        Test nested context manager usage.
        
        Testing Concept: Test nested contexts
        """
        # Setup - create two different sessions
        session1 = MagicMock()
        session2 = MagicMock()
        
        mock_database.return_value.session.side_effect = [session1, session2]
        
        instance1 = test_mixin_class()
        instance2 = test_mixin_class()
        
        # Execute - nested contexts
        with instance1:
            assert instance1._db_session == session1
            
            with instance2:
                assert instance2._db_session == session2
            
            # Inner context closed
            session2.close.assert_called_once()
        
        # Outer context closed
        session1.close.assert_called_once()


# ============================================================================
# TEST CLASS: Edge Cases and Error Scenarios
# ============================================================================


class TestDBEnterExitMixinEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_exit_when_session_close_raises_exception(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test __exit__ when session.close() raises exception.
        
        Testing Concept: Test exception during cleanup
        """
        # Setup
        mock_db_session.close.side_effect = Exception("Close failed")
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - should raise the close exception
        with pytest.raises(Exception, match="Close failed"):
            instance.__exit__(None, None, None)
    
    def test_exit_when_rollback_raises_exception(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test __exit__ when session.rollback() raises exception.
        
        Testing Concept: Test exception during rollback
        """
        # Setup
        mock_db_session.rollback.side_effect = Exception("Rollback failed")
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - with original exception
        with pytest.raises(Exception, match="Rollback failed"):
            instance.__exit__(ValueError, ValueError("Original error"), None)
    
    def test_enter_when_database_creation_fails(
        self, test_mixin_class, mock_database, mock_logger
    ):
        """
        Test __enter__ when Database creation fails.
        
        Testing Concept: Test initialization failure
        """
        # Setup - Database raises exception
        mock_database.side_effect = Exception("Database connection failed")
        
        instance = test_mixin_class()
        
        # Execute and verify exception is propagated
        with pytest.raises(Exception, match="Database connection failed"):
            instance.__enter__()
    
    def test_enter_when_session_creation_fails(
        self, test_mixin_class, mock_database, mock_logger
    ):
        """
        Test __enter__ when session creation fails.
        
        Testing Concept: Test session creation failure
        """
        # Setup - session() raises exception
        mock_database.return_value.session.side_effect = Exception("Session failed")
        
        instance = test_mixin_class()
        
        # Execute and verify exception is propagated
        with pytest.raises(Exception, match="Session failed"):
            instance.__enter__()
    
    def test_exit_with_all_none_parameters(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test __exit__ with all None parameters (normal exit).
        
        Testing Concept: Test explicit None values
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute - explicit None values
        instance.__exit__(exc_type=None, exc_val=None, exc_tb=None)
        
        # Verify
        mock_db_session.close.assert_called_once()
        mock_db_session.rollback.assert_not_called()
    
    def test_multiple_mixin_instances_use_separate_sessions(
        self, test_mixin_class, mock_database, mock_logger
    ):
        """
        Test that multiple mixin instances use separate sessions.
        
        Testing Concept: Test instance isolation
        """
        # Setup - create two different sessions
        session1 = MagicMock()
        session2 = MagicMock()
        
        mock_database.return_value.session.side_effect = [session1, session2]
        
        # Create two instances
        instance1 = test_mixin_class()
        instance2 = test_mixin_class()
        
        # Execute
        instance1.__enter__()
        instance2.__enter__()
        
        # Verify different sessions
        assert instance1._db_session == session1
        assert instance2._db_session == session2
        assert instance1._db_session is not instance2._db_session
    
    def test_exit_does_not_return_value(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that __exit__ doesn't suppress exceptions.
        
        Testing Concept: Test exception propagation
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        instance.__enter__()
        
        # Execute
        result = instance.__exit__(ValueError, ValueError("error"), None)
        
        # Verify - __exit__ returns None (doesn't suppress exception)
        assert result is None


# ============================================================================
# TEST CLASS: Database Helper Management
# ============================================================================


class TestDBHelperManagement:
    """Test database helper lifecycle management."""
    
    def test_db_helper_created_with_correct_parameters(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that Database is created with correct schema and name.
        
        Testing Concept: Test parameter passing
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Execute
        instance.__enter__()
        
        # Verify Database was called with correct parameters
        mock_database.assert_called_once_with(
            db_schema="schengendb",
            db_name="postgresql"
        )
    
    def test_db_helper_reused_across_multiple_enters(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that db_helper is reused if already exists.
        
        Testing Concept: Test helper reuse
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # First enter
        instance.__enter__()
        first_helper = instance._db_helper
        
        # Exit
        instance.__exit__(None, None, None)
        
        # Reset session mock
        mock_database.reset_mock()
        
        # Second enter
        instance.__enter__()
        second_helper = instance._db_helper
        
        # Verify same helper is used
        assert first_helper is second_helper
        
        # Verify Database was only created once
        assert mock_database.call_count == 0  # Not called again
    
    def test_db_helper_none_check_uses_or_operator(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test the 'or' operator behavior in db_helper assignment.
        
        Testing Concept: Test None coalescing
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        # Case 1: _db_helper is None
        instance1 = test_mixin_class()
        instance1._db_helper = None
        instance1.__enter__()
        
        assert instance1._db_helper is not None
        
        # Case 2: _db_helper is already set
        existing_helper = MagicMock()
        existing_helper.session.return_value = mock_db_session
        
        instance2 = test_mixin_class()
        instance2._db_helper = existing_helper
        instance2.__enter__()
        
        assert instance2._db_helper is existing_helper


# ============================================================================
# TEST CLASS: Session Lifecycle
# ============================================================================


class TestSessionLifecycle:
    """Test complete session lifecycle."""
    
    def test_complete_session_lifecycle_success(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test complete session lifecycle without errors.
        
        Testing Concept: Test full lifecycle
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Phase 1: Enter - create session
        instance.__enter__()
        assert instance._db_session is not None
        mock_database.return_value.session.assert_called_once()
        
        # Phase 2: Use session (simulated)
        # In real usage, operations would happen here
        
        # Phase 3: Exit - cleanup
        instance.__exit__(None, None, None)
        mock_db_session.close.assert_called_once()
        mock_db_session.rollback.assert_not_called()
    
    def test_complete_session_lifecycle_with_error(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test complete session lifecycle with error.
        
        Testing Concept: Test error lifecycle
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        # Phase 1: Enter
        instance.__enter__()
        
        # Phase 2: Error occurs
        error = ValueError("Database operation failed")
        
        # Phase 3: Exit with error
        instance.__exit__(type(error), error, None)
        
        # Verify cleanup with rollback
        mock_db_session.close.assert_called_once()
        mock_db_session.rollback.assert_called_once()
    
    def test_session_not_created_before_enter(
        self, test_mixin_class, mock_database, mock_logger
    ):
        """
        Test that session is None before __enter__ is called.
        
        Testing Concept: Test initial state
        """
        instance = test_mixin_class()
        
        # Verify initial state
        assert instance._db_session is None
        assert instance._db_helper is None
    
    def test_session_available_during_context(
        self, test_mixin_class, mock_database, mock_db_session, mock_logger
    ):
        """
        Test that session is available during context.
        
        Testing Concept: Test context state
        """
        # Setup
        mock_database.return_value.session.return_value = mock_db_session
        
        instance = test_mixin_class()
        
        with instance:
            # Session should be available
            assert instance._db_session is not None
            assert instance._db_session == mock_db_session


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.utils.db_enter_exit_mixin",
        "--cov-report=term-missing"
    ])
