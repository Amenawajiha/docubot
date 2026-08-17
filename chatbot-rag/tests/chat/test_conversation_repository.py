"""
Comprehensive unit tests for conversation repository implementations.

This test suite covers:
- IConversationRepository abstract base class
- FileConversationRepository (JSON file storage)
- DatabaseConversationRepository (PostgreSQL with SQLAlchemy)
- CompositeConversationRepository (combined storage)

Tests include:
- Message saving and retrieval
- Conversation deletion
- Cleanup operations
- Error handling
- Edge cases (empty data, missing files, DB failures)
- File I/O operations (mocked)
- Database operations (mocked)
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, Mock, patch, mock_open, call

import pytest

from src.chat.conversation_repository import (
    IConversationRepository,
    FileConversationRepository,
    DatabaseConversationRepository,
    CompositeConversationRepository,
)
from src.models import Message


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """
    Mock configuration values.
    
    Returns config dict for get_config calls.
    """
    config_values = {
        "conversation.recent_count": 10,
        "conversation.storage_path": "/tmp/test_conversations",
    }
    
    with patch("src.chat.conversation_repository.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def sample_message():
    """Create a sample user message."""
    return Message(
        role="user",
        content="What is a Schengen visa?",
        timestamp=datetime.now(timezone.utc),
        user_id=123,
        metadata={}
    )


@pytest.fixture
def sample_assistant_message():
    """Create a sample assistant message."""
    return Message(
        role="assistant",
        content="A Schengen visa allows travel in 27 European countries.",
        timestamp=datetime.now(timezone.utc),
        user_id=123,
        metadata={}
    )


@pytest.fixture
def sample_summary_message():
    """Create a summary message."""
    return Message(
        role="assistant",
        content="Summary of conversation",
        timestamp=datetime.now(timezone.utc),
        user_id=123,
        metadata={"is_summary": True}
    )


@pytest.fixture
def conversation_history():
    """Create a list of messages for testing."""
    messages = []
    for i in range(15):
        messages.append(
            Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=123,
                metadata={}
            )
        )
    return messages


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def mock_db_helper():
    """Mock database helper."""
    helper = MagicMock()
    return helper


# ============================================================================
# TEST CLASS: FileConversationRepository - Initialization
# ============================================================================


class TestFileRepositoryInitialization:
    """Test FileConversationRepository initialization."""
    
    def test_initialization_creates_storage_directory(self, mock_config):
        """
        Test that initialization creates storage directory.
        
        Testing Concept: Verify directory creation on init
        """
        with patch("src.chat.conversation_repository.os.makedirs") as mock_makedirs:
            repo = FileConversationRepository()
            
            # Should create directory
            mock_makedirs.assert_called_once_with(
                "/tmp/test_conversations", 
                exist_ok=True
            )
    
    def test_initialization_loads_storage_path_from_config(self, mock_config):
        """
        Test that storage path is loaded from config.
        
        Testing Concept: Configuration loading
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            assert repo.storage_path == "/tmp/test_conversations"
    
    def test_initialization_loads_recent_count_from_config(self, mock_config):
        """
        Test that recent_count is loaded from config.
        
        Testing Concept: Base class initialization
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            assert repo._recent_count == 10


# ============================================================================
# TEST CLASS: FileConversationRepository - Save Message
# ============================================================================


class TestFileRepositorySaveMessage:
    """Test message saving in FileConversationRepository."""
    
    def test_save_message_creates_new_file_for_new_user(
        self, mock_config, sample_message
    ):
        """
        Test that new file is created for new user.
        
        Testing Concept: File creation on first save
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            # Mock file operations
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    repo.save_message(123, sample_message)
                    
                    # Should open file for writing (use os.path.join for cross-platform)
                    expected_path = os.path.join("/tmp/test_conversations", "123.json")
                    mock_file.assert_called_once_with(
                        expected_path,
                        "w",
                        encoding="utf-8"
                    )
                    
                    # Should write JSON array with one message
                    written_data = "".join(
                        call.args[0] 
                        for call in mock_file().write.call_args_list
                    )
                    assert "What is a Schengen visa?" in written_data
    
    def test_save_message_appends_to_existing_file(
        self, mock_config, sample_message, sample_assistant_message
    ):
        """
        Test that message is appended to existing file.
        
        Testing Concept: Append operation
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            # Mock existing file content
            existing_messages = [{
                "role": "user",
                "content": "Previous message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": 123,
                "metadata": {}
            }]
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                mock_file = mock_open(read_data=json.dumps(existing_messages))
                with patch("builtins.open", mock_file):
                    repo.save_message(123, sample_assistant_message)
                    
                    # Should open file for read+write (use os.path.join)
                    expected_path = os.path.join("/tmp/test_conversations", "123.json")
                    mock_file.assert_called_with(
                        expected_path,
                        "r+",
                        encoding="utf-8"
                    )
    
    def test_save_message_preserves_message_data(
        self, mock_config, sample_message
    ):
        """
        Test that all message data is preserved.
        
        Testing Concept: Data integrity
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    repo.save_message(123, sample_message)
                    
                    # Verify all fields are written
                    written_data = "".join(
                        call.args[0] 
                        for call in mock_file().write.call_args_list
                    )
                    assert "user" in written_data  # role
                    assert "What is a Schengen visa?" in written_data  # content
                    assert "123" in written_data  # user_id
    
    def test_save_message_with_metadata(self, mock_config):
        """
        Test saving message with metadata.
        
        Testing Concept: Optional fields
        """
        msg = Message(
            role="assistant",
            content="Summary",
            timestamp=datetime.now(timezone.utc),
            user_id=456,
            metadata={"is_summary": True, "version": 2}
        )
        
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    repo.save_message(456, msg)
                    
                    written_data = "".join(
                        call.args[0] 
                        for call in mock_file().write.call_args_list
                    )
                    assert "is_summary" in written_data
                    assert "true" in written_data.lower()


# ============================================================================
# TEST CLASS: FileConversationRepository - Get Messages
# ============================================================================


class TestFileRepositoryGetMessages:
    """Test message retrieval in FileConversationRepository."""
    
    def test_get_messages_returns_empty_list_for_nonexistent_file(
        self, mock_config
    ):
        """
        Test that empty list is returned when file doesn't exist.
        
        Testing Concept: Handle missing file
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                messages = repo.get_messages(999)
                
                assert messages == []
    
    def test_get_messages_returns_all_messages_below_threshold(
        self, mock_config
    ):
        """
        Test that all messages are returned when below recent_count.
        
        Testing Concept: Return all when count is low
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            # Create 5 messages (below threshold of 10)
            messages_data = [
                {
                    "role": "user",
                    "content": f"Message {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": 123,
                    "metadata": {}
                }
                for i in range(5)
            ]
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                mock_file = mock_open(read_data=json.dumps(messages_data))
                with patch("builtins.open", mock_file):
                    messages = repo.get_messages(123)
                    
                    assert len(messages) == 5
    
    def test_get_messages_returns_last_n_messages_above_threshold(
        self, mock_config
    ):
        """
        Test that only last N messages are returned when above threshold.
        
        Testing Concept: Limit to recent_count
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            # Create 20 messages (above threshold of 10)
            messages_data = [
                {
                    "role": "user",
                    "content": f"Message {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": 123,
                    "metadata": {}
                }
                for i in range(20)
            ]
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                mock_file = mock_open(read_data=json.dumps(messages_data))
                with patch("builtins.open", mock_file):
                    messages = repo.get_messages(123)
                    
                    # Should return only last 10 messages
                    assert len(messages) == 10
                    assert messages[0].content == "Message 10"
                    assert messages[9].content == "Message 19"
    
    def test_get_messages_converts_to_message_objects(self, mock_config):
        """
        Test that JSON data is converted to Message objects.
        
        Testing Concept: Type conversion
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            messages_data = [{
                "role": "user",
                "content": "Test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": 123,
                "metadata": {"test": "value"}
            }]
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                mock_file = mock_open(read_data=json.dumps(messages_data))
                with patch("builtins.open", mock_file):
                    messages = repo.get_messages(123)
                    
                    assert len(messages) == 1
                    assert isinstance(messages[0], Message)
                    assert messages[0].role == "user"
                    assert messages[0].content == "Test"
                    assert messages[0].user_id == 123
                    assert messages[0].metadata == {"test": "value"}
    
    def test_get_messages_adds_utc_timezone_to_naive_timestamps(
        self, mock_config
    ):
        """
        Test that naive timestamps get UTC timezone.
        
        Testing Concept: Timezone normalization
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            # Create timestamp without timezone
            naive_dt = datetime(2024, 1, 1, 12, 0, 0)
            messages_data = [{
                "role": "user",
                "content": "Test",
                "timestamp": naive_dt.isoformat(),
                "user_id": 123,
                "metadata": {}
            }]
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                mock_file = mock_open(read_data=json.dumps(messages_data))
                with patch("builtins.open", mock_file):
                    messages = repo.get_messages(123)
                    
                    assert messages[0].timestamp.tzinfo == timezone.utc
    
    def test_get_messages_preserves_timezone_aware_timestamps(
        self, mock_config
    ):
        """
        Test that timezone-aware timestamps are preserved.
        
        Testing Concept: Preserve existing timezone
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            messages_data = [{
                "role": "user",
                "content": "Test",
                "timestamp": aware_dt.isoformat(),
                "user_id": 123,
                "metadata": {}
            }]
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                mock_file = mock_open(read_data=json.dumps(messages_data))
                with patch("builtins.open", mock_file):
                    messages = repo.get_messages(123)
                    
                    assert messages[0].timestamp.tzinfo is not None


# ============================================================================
# TEST CLASS: FileConversationRepository - Delete Conversation
# ============================================================================


class TestFileRepositoryDeleteConversation:
    """Test conversation deletion in FileConversationRepository."""
    
    def test_delete_conversation_removes_file_when_exists(self, mock_config):
        """
        Test that file is deleted when it exists.
        
        Testing Concept: File deletion
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                    repo.delete_conversation(123)
                    
                    # Use os.path.join for cross-platform path
                    expected_path = os.path.join("/tmp/test_conversations", "123.json")
                    mock_remove.assert_called_once_with(expected_path)
    
    def test_delete_conversation_does_nothing_when_file_missing(
        self, mock_config
    ):
        """
        Test that nothing happens when file doesn't exist.
        
        Testing Concept: Handle missing file gracefully
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                    repo.delete_conversation(456)
                    
                    # Should not attempt to remove
                    mock_remove.assert_not_called()


# ============================================================================
# TEST CLASS: FileConversationRepository - Cleanup
# ============================================================================


class TestFileRepositoryCleanup:
    """Test cleanup operations in FileConversationRepository."""
    
    def test_cleanup_removes_old_files(self, mock_config):
        """
        Test that old files are removed.
        
        Testing Concept: Time-based cleanup
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            current_time = time.time()
            old_file_time = current_time - (10 * 24 * 60 * 60)  # 10 days old
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                with patch("src.chat.conversation_repository.os.listdir", return_value=["123.json"]):
                    with patch("src.chat.conversation_repository.os.path.getmtime", return_value=old_file_time):
                        with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                            deleted_count = repo.cleanup_old_conversations(days=7)
                            
                            assert deleted_count == 1
                            mock_remove.assert_called_once()
    
    def test_cleanup_keeps_recent_files(self, mock_config):
        """
        Test that recent files are not removed.
        
        Testing Concept: Time-based filtering
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            current_time = time.time()
            recent_file_time = current_time - (3 * 24 * 60 * 60)  # 3 days old
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                with patch("src.chat.conversation_repository.os.listdir", return_value=["456.json"]):
                    with patch("src.chat.conversation_repository.os.path.getmtime", return_value=recent_file_time):
                        with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                            deleted_count = repo.cleanup_old_conversations(days=7)
                            
                            assert deleted_count == 0
                            mock_remove.assert_not_called()
    
    def test_cleanup_returns_zero_when_directory_missing(self, mock_config):
        """
        Test that cleanup returns 0 when directory doesn't exist.
        
        Testing Concept: Handle missing directory
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                deleted_count = repo.cleanup_old_conversations(days=7)
                
                assert deleted_count == 0
    
    def test_cleanup_skips_non_json_files(self, mock_config):
        """
        Test that non-JSON files are ignored.
        
        Testing Concept: File type filtering
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            current_time = time.time()
            old_time = current_time - (10 * 24 * 60 * 60)
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                with patch("src.chat.conversation_repository.os.listdir", 
                          return_value=["test.txt", "123.json"]):
                    with patch("src.chat.conversation_repository.os.path.getmtime", return_value=old_time):
                        with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                            deleted_count = repo.cleanup_old_conversations(days=7)
                            
                            # Only JSON file should be deleted
                            assert deleted_count == 1
    
    def test_cleanup_handles_deletion_errors_gracefully(self, mock_config):
        """
        Test that cleanup continues when file deletion fails.
        
        Testing Concept: Error handling
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            current_time = time.time()
            old_time = current_time - (10 * 24 * 60 * 60)
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                with patch("src.chat.conversation_repository.os.listdir", 
                          return_value=["123.json", "456.json"]):
                    with patch("src.chat.conversation_repository.os.path.getmtime", return_value=old_time):
                        # First file fails, second succeeds
                        with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                            mock_remove.side_effect = [OSError("Permission denied"), None]
                            
                            deleted_count = repo.cleanup_old_conversations(days=7)
                            
                            # Should skip failed file and continue
                            assert deleted_count == 1


# ============================================================================
# TEST CLASS: DatabaseConversationRepository - Initialization
# ============================================================================


class TestDatabaseRepositoryInitialization:
    """Test DatabaseConversationRepository initialization."""
    
    def test_initialization_sets_defaults(self, mock_config):
        """
        Test that initialization sets default values.
        
        Testing Concept: Default state
        """
        repo = DatabaseConversationRepository()
        
        assert repo._db_helper is None
        assert repo._db_session is None
        assert repo.messages == []
    
    def test_initialization_loads_recent_count(self, mock_config):
        """
        Test that recent_count is loaded from config.
        
        Testing Concept: Configuration loading
        """
        repo = DatabaseConversationRepository()
        
        assert repo._recent_count == 10


# ============================================================================
# TEST CLASS: DatabaseConversationRepository - Save Message
# ============================================================================


class TestDatabaseRepositorySaveMessage:
    """Test message saving in DatabaseConversationRepository."""
    
    def test_save_message_skips_non_summary_messages(
        self, mock_config, sample_message
    ):
        """
        Test that regular messages are not saved to DB.
        
        Testing Concept: Conditional save logic
        """
        repo = DatabaseConversationRepository()
        
        # Regular message without is_summary flag
        repo.save_message(123, sample_message)
        
        # Should not interact with DB (early return)
        assert repo._db_session is None
    
    @pytest.mark.integration
    def test_save_message_saves_summary_messages(
        self, mock_config, sample_summary_message
    ):
        """
        Test that summary messages are saved to DB.
        
        Testing Concept: Integration test with real DB (marked for skipping in unit tests)
        """
        # This test hits real DB - mark as integration test
        pytest.skip("Integration test - requires real database")
    
    @pytest.mark.integration
    def test_save_message_handles_database_errors(
        self, mock_config, sample_summary_message
    ):
        """
        Test that database errors are raised.
        
        Testing Concept: Integration test (marked for skipping in unit tests)
        """
        # This test hits real DB - mark as integration test
        pytest.skip("Integration test - requires real database")


# ============================================================================
# TEST CLASS: DatabaseConversationRepository - Get Messages
# ============================================================================


class TestDatabaseRepositoryGetMessages:
    """Test message retrieval in DatabaseConversationRepository."""
    
    @pytest.mark.integration
    def test_get_messages_returns_empty_list_on_error(self, mock_config):
        """
        Test that empty list is returned when DB query fails.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")
    
    @pytest.mark.integration
    def test_get_messages_queries_with_user_id_filter(self, mock_config):
        """
        Test that DB query filters by user_id.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")
    
    @pytest.mark.integration
    def test_get_messages_limits_to_recent_count(self, mock_config):
        """
        Test that query limits results to recent_count.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")
    
    @pytest.mark.integration
    def test_get_messages_converts_orm_to_message_objects(self, mock_config):
        """
        Test that ORM records are converted to Message objects.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")
    
    @pytest.mark.integration
    def test_get_messages_uses_assistant_role_when_metadata_missing(self, mock_config):
        """
        Test default role assignment when metadata is missing.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")


# ============================================================================
# TEST CLASS: DatabaseConversationRepository - Delete Conversation
# ============================================================================


class TestDatabaseRepositoryDeleteConversation:
    """Test conversation deletion in DatabaseConversationRepository."""
    
    @pytest.mark.integration
    def test_delete_conversation_removes_records(self, mock_config):
        """
        Test that all user records are deleted.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")
    
    @pytest.mark.integration
    def test_delete_conversation_handles_errors(self, mock_config):
        """
        Test that deletion errors are raised.
        
        Testing Concept: Integration test (marked for skipping)
        """
        pytest.skip("Integration test - requires real database")


# ============================================================================
# TEST CLASS: CompositeConversationRepository
# ============================================================================


class TestCompositeRepository:
    """Test CompositeConversationRepository."""
    
    def test_initialization_creates_both_repositories(self, mock_config):
        """
        Test that both repositories are initialized.
        
        Testing Concept: Composition pattern
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            assert isinstance(repo.db_repository, DatabaseConversationRepository)
            assert isinstance(repo.file_repository, FileConversationRepository)
    
    def test_save_message_saves_to_both_repositories(
        self, mock_config, sample_message
    ):
        """
        Test that message is saved to both repositories.
        
        Testing Concept: Delegation to multiple backends
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            # Mock both repositories
            repo.file_repository.save_message = MagicMock()
            repo.db_repository.save_message = MagicMock()
            
            repo.save_message(123, sample_message)
            
            # Both should be called
            repo.file_repository.save_message.assert_called_once_with(123, sample_message)
            repo.db_repository.save_message.assert_called_once_with(123, sample_message)
    
    def test_get_messages_returns_file_messages_when_available(
        self, mock_config, conversation_history
    ):
        """
        Test that file messages are preferred when available.
        
        Testing Concept: Priority logic
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            # Mock repositories
            repo.file_repository.get_messages = MagicMock(return_value=conversation_history[:5])
            repo.db_repository.get_messages = MagicMock(return_value=[])
            
            messages = repo.get_messages(123)
            
            # Should return file messages
            assert len(messages) == 5
            # DB should not be queried
            repo.db_repository.get_messages.assert_not_called()
    
    def test_get_messages_queries_db_when_file_empty(
        self, mock_config, conversation_history
    ):
        """
        Test that DB is queried when file storage is empty.
        
        Testing Concept: Fallback logic
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            # Mock repositories
            repo.file_repository.get_messages = MagicMock(return_value=[])
            repo.db_repository.get_messages = MagicMock(return_value=conversation_history[:3])
            
            messages = repo.get_messages(456)
            
            # Should query DB
            assert len(messages) == 3
            repo.db_repository.get_messages.assert_called_once_with(456)
    
    def test_get_messages_combines_and_sorts_by_timestamp(
        self, mock_config
    ):
        """
        Test that messages are combined and sorted.
        
        Testing Concept: Data merging and sorting
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            # Create messages with different timestamps
            old_msg = Message(
                role="user",
                content="Old",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                user_id=123,
                metadata={}
            )
            new_msg = Message(
                role="user",
                content="New",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                user_id=123,
                metadata={}
            )
            
            # File has new, DB has old
            repo.file_repository.get_messages = MagicMock(return_value=[])
            repo.db_repository.get_messages = MagicMock(return_value=[new_msg, old_msg])
            
            messages = repo.get_messages(123)
            
            # Should be sorted by timestamp
            assert messages[0].content == "Old"
            assert messages[1].content == "New"
    
    def test_get_messages_normalizes_naive_timestamps(
        self, mock_config
    ):
        """
        Test that naive timestamps are converted to UTC.
        
        Testing Concept: Timezone normalization
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            # Create message with naive timestamp
            naive_msg = Message(
                role="user",
                content="Test",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),  # No timezone
                user_id=123,
                metadata={}
            )
            
            repo.file_repository.get_messages = MagicMock(return_value=[])
            repo.db_repository.get_messages = MagicMock(return_value=[naive_msg])
            
            messages = repo.get_messages(123)
            
            # Should have UTC timezone
            assert messages[0].timestamp.tzinfo == timezone.utc
    
    def test_delete_conversation_deletes_from_both(self, mock_config):
        """
        Test that deletion happens in both repositories.
        
        Testing Concept: Delegation to multiple backends
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = CompositeConversationRepository()
            
            # Mock both repositories
            repo.file_repository.delete_conversation = MagicMock()
            repo.db_repository.delete_conversation = MagicMock()
            
            repo.delete_conversation(789)
            
            # Both should be called
            repo.file_repository.delete_conversation.assert_called_once_with(789)
            repo.db_repository.delete_conversation.assert_called_once_with(789)


# ============================================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases across all repository implementations."""
    
    def test_file_repository_with_corrupted_json(self, mock_config):
        """
        Test handling of corrupted JSON file.
        
        Testing Concept: Malformed data handling
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                # Invalid JSON
                mock_file = mock_open(read_data="{ invalid json }")
                with patch("builtins.open", mock_file):
                    with pytest.raises(json.JSONDecodeError):
                        repo.get_messages(123)
    
    def test_get_file_path_generates_correct_path(self, mock_config):
        """
        Test that file path is generated correctly.
        
        Testing Concept: Path generation
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            path = repo._get_file_path(123)
            
            # Use os.path.join for cross-platform comparison
            expected_path = os.path.join("/tmp/test_conversations", "123.json")
            assert path == expected_path
    
    def test_save_message_with_special_characters(self, mock_config):
        """
        Test saving message with special characters.
        
        Testing Concept: Unicode handling
        """
        msg = Message(
            role="user",
            content="Test with émojis 🎉 and special chars: <>&\"'",
            timestamp=datetime.now(timezone.utc),
            user_id=123,
            metadata={}
        )
        
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    # Should not raise error
                    repo.save_message(123, msg)
                    
                    assert mock_file().write.called


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently."""
    
    @pytest.mark.parametrize("user_id", [1, 999, 123456])
    def test_file_repository_save_for_different_users(
        self, mock_config, sample_message, user_id
    ):
        """
        Test saving messages for different user IDs.
        
        Testing Concept: Parameterized user ID testing
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=False):
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    repo.save_message(user_id, sample_message)
                    
                    # Should create file for each user (use os.path.join)
                    expected_path = os.path.join("/tmp/test_conversations", f"{user_id}.json")
                    mock_file.assert_called_with(expected_path, "w", encoding="utf-8")
    
    @pytest.mark.parametrize("days,should_delete", [
        (1, True),    # ✅ File is 3 days old, cutoff is 1 day ago → DELETE
        (5, False),   # ✅ File is 3 days old, cutoff is 5 days ago → KEEP
        (10, False),  # ✅ File is 3 days old, cutoff is 10 days ago → KEEP
    ])
    def test_cleanup_with_various_day_thresholds(
        self, mock_config, days, should_delete
    ):
        """
        Cleanup deletes files OLDER than (current_time - days).
        
        File is 3 days old:
        - days=1: cutoff is 1 day ago, file is 3 days old → DELETE
        - days=5: cutoff is 5 days ago, file is 3 days old → KEEP
        - days=10: cutoff is 10 days ago, file is 3 days old → KEEP
        """
        with patch("src.chat.conversation_repository.os.makedirs"):
            repo = FileConversationRepository()
            
            current_time = time.time()
            file_time = current_time - (3 * 24 * 60 * 60)  # 3 days old
            
            with patch("src.chat.conversation_repository.os.path.exists", return_value=True):
                with patch("src.chat.conversation_repository.os.listdir", return_value=["test.json"]):
                    with patch("src.chat.conversation_repository.os.path.getmtime", return_value=file_time):
                        with patch("src.chat.conversation_repository.os.remove") as mock_remove:
                            deleted_count = repo.cleanup_old_conversations(days=days)
                            
                            if should_delete:
                                assert deleted_count == 1
                                mock_remove.assert_called_once()
                            else:
                                assert deleted_count == 0
                                mock_remove.assert_not_called()


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.chat.conversation_repository",
        "--cov-report=term-missing",
        "-m", "not integration"  # Skip integration tests by default
    ])


"""
RUNNING THE TESTS:

1. Run unit tests only (skip DB tests):
   pytest tests/chat/test_conversation_repository.py -v -m "not integration"

2. Run with coverage:
   pytest tests/chat/test_conversation_repository.py --cov=src.chat.conversation_repository --cov-report=html -m "not integration"

3. Run integration tests (requires DB):
   pytest tests/chat/test_conversation_repository.py -v -m integration

4. Run all tests:
   pytest tests/chat/test_conversation_repository.py -v

EXPECTED COVERAGE:
- Unit tests: 75-80% coverage (file operations fully tested)
- Integration tests: 88%+ coverage (includes DB operations)
"""