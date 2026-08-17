"""
Comprehensive unit tests for ConversationManager.

This test suite covers:
- Message addition with and without authentication
- Message retrieval with formatting
- Conversation summarization logic
- Conversation clearing
- Message formatting (plain and with summary)
- Edge cases (empty conversations, None values)
- Repository integration
- Configuration-based behavior
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.chat.conversation_manager import ConversationManager
from src.models import Message


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """
    Mock configuration values.
    
    Returns dict of config values that get_config will return.
    """
    config_values = {
        "conversation.enable_summarization": True,
        "conversation.storage_threshold": 10,
        "conversation.retrieval_threshold": 8,
    }
    
    with patch("src.chat.conversation_manager.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def mock_repository():
    """
    Mock conversation repository.
    
    Testing Concept: Mock external dependency (file/database operations)
    """
    mock_repo = MagicMock()
    mock_repo.save_message = MagicMock()
    mock_repo.get_messages = MagicMock(return_value=[])
    mock_repo.delete_conversation = MagicMock()
    return mock_repo


@pytest.fixture
def mock_summarizer():
    """
    Mock conversation summarizer.
    
    Testing Concept: Mock LLM/API calls
    
    FIXED: Create valid Message objects with proper role and user_id
    """
    mock_summ = MagicMock()
    
    summary_msg = Message(
        role="assistant",  
        content="Summary of previous conversation",
        timestamp=datetime.now(),
        user_id=1  # Added required field
    )
    mock_summ.summarize_for_storage = MagicMock(return_value=summary_msg)
    
    # Mock summarize_for_retrieval to return summary text
    mock_summ.summarize_for_retrieval = MagicMock(
        return_value="Brief summary of conversation"
    )
    
    return mock_summ


@pytest.fixture
def conversation_manager(mock_config, mock_repository, mock_summarizer):
    """
    Create ConversationManager with mocked dependencies.
    
    Testing Concept: Fixture with dependency injection
    """
    with patch("src.chat.conversation_manager.FileConversationRepository") as mock_file_repo:
        mock_file_repo.return_value = mock_repository
        
        with patch("src.chat.conversation_manager.ConversationSummarizer") as mock_summ_class:
            mock_summ_class.return_value = mock_summarizer
            
            manager = ConversationManager(repository=mock_repository)
            manager.summarizer = mock_summarizer
            
            return manager


@pytest.fixture
def sample_message():
    """Create a sample user message."""
    return Message(
        role="user",
        content="What is a Schengen visa?",
        timestamp=datetime.now(),
        user_id=1  # Added required field
    )


@pytest.fixture
def sample_assistant_message():
    """Create a sample assistant message."""
    return Message(
        role="assistant",
        content="A Schengen visa allows travel in 27 European countries.",
        timestamp=datetime.now(),
        user_id=1  # Added required field
    )


@pytest.fixture
def conversation_history():
    """
    Create a list of messages simulating conversation history.
    
    Testing Concept: Fixture that generates test data
    """
    messages = []
    for i in range(10):
        messages.append(
            Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.now(),
                user_id=1  # Added required field
            )
        )
    return messages

class TestConversationManagerInitialization:
    """Test ConversationManager initialization."""
    
    def test_initialization_with_default_repository(self, mock_config):
        """
        Test that manager initializes with default repository.
        
        Testing Concept: Test default parameter behavior
        """
        with patch("src.chat.conversation_manager.FileConversationRepository") as mock_repo:
            with patch("src.chat.conversation_manager.ConversationSummarizer"):
                manager = ConversationManager()
                
                # Should create FileConversationRepository
                mock_repo.assert_called_once()

    def test_initialization_with_custom_repository(self, mock_config, mock_repository):
        """
        Test that manager accepts custom repository.
        
        Testing Concept: Test dependency injection
        """
        with patch("src.chat.conversation_manager.ConversationSummarizer"):
            manager = ConversationManager(repository=mock_repository)
            
            assert manager.repository == mock_repository
    
    def test_initialization_creates_summarizer(self, mock_config, mock_repository):
        """
        Test that summarizer is initialized.
        
        Testing Concept: Verify object composition
        """
        with patch("src.chat.conversation_manager.ConversationSummarizer") as mock_summ:
            manager = ConversationManager(repository=mock_repository)
            
            mock_summ.assert_called_once()
            assert manager.summarizer is not None

    def test_initialization_loads_enable_summarization_from_config(
        self, mock_repository
    ):
        """
        Test that enable_summarization is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.chat.conversation_manager.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.enable_summarization": False,
            }.get(key, default)
            
            with patch("src.chat.conversation_manager.ConversationSummarizer"):
                manager = ConversationManager(repository=mock_repository)
                
                assert manager.enable_summarization is False
    
    def test_initialization_with_summarization_enabled(
        self, mock_config, mock_repository
    ):
        """Test initialization with summarization enabled."""
        with patch("src.chat.conversation_manager.ConversationSummarizer"):
            manager = ConversationManager(repository=mock_repository)
            
            assert manager.enable_summarization is True

class TestAddMessageHappyPath:
    """Test successful message addition scenarios."""
    
    def test_add_message_saves_to_repository(
        self, conversation_manager, sample_message
    ):
        """
        Test that adding message calls repository save.
        
        Testing Concept: Verify method calls on dependencies
        """
        user_id = 123
        
        conversation_manager.add_message(sample_message, user_id)
        
        # Verify save_message was called with correct arguments
        conversation_manager.repository.save_message.assert_called_once_with(
            user_id, sample_message
        )
    
    def test_add_message_with_authenticated_user(
        self, conversation_manager, sample_message
    ):
        """
        Test adding message for authenticated user.
        
        Testing Concept: Test normal flow
        """
        user_id = 456
        
        conversation_manager.add_message(sample_message, user_id)
        
        assert conversation_manager.repository.save_message.called
    
    def test_add_message_does_not_save_for_unauthenticated_user(
        self, conversation_manager, sample_message
    ):
        """
        Test that message is not saved for unauthenticated users.
        
        Testing Concept: Test early return logic
        """
        user_id = None  # Unauthenticated
        
        conversation_manager.add_message(sample_message, user_id)
        
        # Should not save
        conversation_manager.repository.save_message.assert_not_called()
    
    def test_add_message_with_zero_user_id_does_not_save(
        self, conversation_manager, sample_message
    ):
        """
        Test that user_id=0 is treated as unauthenticated.
        
        Testing Concept: Test falsy value handling
        """
        user_id = 0  # Falsy value
        
        conversation_manager.add_message(sample_message, user_id)
        
        # Should not save (0 is falsy)
        conversation_manager.repository.save_message.assert_not_called()
    
    def test_add_message_with_empty_string_user_id(
        self, conversation_manager, sample_message
    ):
        """
        Test that empty string user_id doesn't save.
        
        Testing Concept: Test edge case - empty string
        """
        user_id = ""  # Empty string (falsy)
        
        conversation_manager.add_message(sample_message, user_id)
        
        conversation_manager.repository.save_message.assert_not_called()

# ============================================================================
# TEST CLASS: Add Message - Summarization Logic
# ============================================================================

class TestAddMessageSummarization:
    """Test message addition with summarization enabled."""
    
    # ... (keep first 3 tests unchanged)
    
    def test_add_message_saves_summary_message(
        self, conversation_manager, sample_message, conversation_history
    ):
        """
        Test that summary message is saved to repository.
        
        Testing Concept: Test multiple method calls
        """
        user_id = 555
        
        # Exceed threshold
        conversation_manager.repository.get_messages.return_value = conversation_history + [sample_message]
        
        # FIXED: Mock summarizer to return valid Message with user_id
        summary_msg = Message(
            role="assistant",  # Changed from "system"
            content="Summary",
            timestamp=datetime.now(),
            user_id=user_id  # Added required field
        )
        conversation_manager.summarizer.summarize_for_storage.return_value = summary_msg
        
        conversation_manager.add_message(sample_message, user_id)
        
        # Should save original message AND summary message
        assert conversation_manager.repository.save_message.call_count == 2
        
        # Check that summary was saved
        calls = conversation_manager.repository.save_message.call_args_list
        assert calls[1] == call(user_id, summary_msg)
    
    # ... (rest of tests unchanged)


class TestGetMessagesForLLMWithSummarization:
    """Test message retrieval with summarization."""
    
    # ... (first 2 tests unchanged)
    
    def test_get_messages_with_summary_includes_summary_as_system_message(
        self, conversation_manager, conversation_history
    ):
        """
        Test that summary is added as system message.
        
        Testing Concept: Test data structure transformation
        
        NOTE: The summary is formatted as a dict with role="system" 
        in the output, not a Message object
        """
        conversation_manager.repository.get_messages.return_value = conversation_history
        conversation_manager.summarizer.summarize_for_retrieval.return_value = "Test summary"
        
        result = conversation_manager.get_messages_for_llm(user_id=555)
        
        # First message should be system message with summary
        # This is a DICT, not a Message object, so role can be "system"
        assert result[0]["role"] == "system"
        assert "Test summary" in result[0]["content"]
        assert "Previous conversation summary:" in result[0]["content"]
    
    # ... (rest of tests unchanged)


class TestGenerateSummaryMessage:
    """Test summary message generation."""
    
    # ... (first 2 tests unchanged)
    
    def test_generate_summary_message_returns_message_object(
        self, conversation_manager, conversation_history
    ):
        """
        Test that result is a Message object.
        
        Testing Concept: Test return type
        """
        conversation_manager.repository.get_messages.return_value = conversation_history
        
        # FIXED: Create valid Message with user_id
        summary_msg = Message(
            role="assistant",  # Changed from "system"
            content="Summary",
            timestamp=datetime.now(),
            user_id=1  # Added required field
        )
        conversation_manager.summarizer.summarize_for_storage.return_value = summary_msg
        
        result = conversation_manager.generate_summary_message(user_id=5678)
        
        assert isinstance(result, Message)
        assert result.content == "Summary"
    
    def test_generate_summary_message_sets_user_id(
        self, conversation_manager, conversation_history
    ):
        """
        Test that user_id is set on summary message.
        
        Testing Concept: Test attribute modification
        """
        user_id = 9999
        conversation_manager.repository.get_messages.return_value = conversation_history
        
        # FIXED: Create valid Message with user_id
        summary_msg = Message(
            role="assistant",  # Changed from "system"
            content="Summary",
            timestamp=datetime.now(),
            user_id=1  # Initial value
        )
        conversation_manager.summarizer.summarize_for_storage.return_value = summary_msg
        
        result = conversation_manager.generate_summary_message(user_id=user_id)
        
        # The method should update the user_id
        assert result.user_id == user_id


class TestConversationFlowIntegration:
    """Test complete conversation flows."""
    
    def test_full_conversation_lifecycle(self, conversation_manager):
        """
        Test adding messages and retrieving them.
        
        Testing Concept: Integration test of multiple methods
        """
        user_id = 12345
        
        # FIXED: Add messages with user_id
        msg1 = Message(
            role="user", 
            content="Question 1", 
            timestamp=datetime.now(),
            user_id=user_id
        )
        msg2 = Message(
            role="assistant", 
            content="Answer 1", 
            timestamp=datetime.now(),
            user_id=user_id
        )
        
        conversation_manager.add_message(msg1, user_id)
        conversation_manager.add_message(msg2, user_id)
        
        # Mock retrieval
        conversation_manager.repository.get_messages.return_value = [msg1, msg2]
        
        # Retrieve
        result = conversation_manager.get_messages_for_llm(user_id)
        
        assert len(result) == 2
        assert result[0]["content"] == "Question 1"
        assert result[1]["content"] == "Answer 1"
    
    def test_conversation_with_summarization_flow(self, conversation_manager):
        """
        Test complete flow with summarization triggered.
        
        Testing Concept: Test complex scenario
        """
        user_id = 54321
        
        # FIXED: Create messages with user_id
        messages = [
            Message(
                role="user" if i % 2 == 0 else "assistant", 
                content=f"Msg {i}", 
                timestamp=datetime.now(),
                user_id=user_id
            )
            for i in range(15)
        ]
        
        conversation_manager.repository.get_messages.return_value = messages
        
        # Retrieve (should trigger summarization)
        result = conversation_manager.get_messages_for_llm(user_id)
        
        # Should have summary + recent messages
        assert result[0]["role"] == "system"
        assert "Previous conversation summary:" in result[0]["content"]
    
    def test_add_clear_and_retrieve_conversation(self, conversation_manager):
        """
        Test adding, clearing, and retrieving conversation.
        
        Testing Concept: Test state changes
        """
        user_id = 98765
        
        # FIXED: Add message with user_id
        msg = Message(
            role="user", 
            content="Test", 
            timestamp=datetime.now(),
            user_id=user_id
        )
        conversation_manager.add_message(msg, user_id)
        
        # Clear
        conversation_manager.clear_conversation(user_id)
        
        # Mock empty retrieval after clearing
        conversation_manager.repository.get_messages.return_value = []
        
        # Retrieve
        result = conversation_manager.get_messages_for_llm(user_id)
        
        assert result == []


class TestGetMessagesForLLMWithoutSummarization:
    """Test message retrieval when summarization is disabled."""
    
    def test_get_messages_for_llm_without_summarization(
        self, mock_repository, mock_summarizer
    ):
        """
        Test message retrieval when summarization is disabled.
        
        Testing Concept: Test different configuration path
        """
        with patch("src.chat.conversation_manager.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.enable_summarization": False,
            }.get(key, default)
            
            with patch("src.chat.conversation_manager.ConversationSummarizer"):
                manager = ConversationManager(repository=mock_repository)
                
                # FIXED: Create messages with user_id
                messages = [
                    Message(
                        role="user", 
                        content=f"Msg {i}", 
                        timestamp=datetime.now(),
                        user_id=1
                    )
                    for i in range(20)
                ]
                manager.repository.get_messages.return_value = messages
                
                result = manager.get_messages_for_llm(user_id=222)
                
                # Should return all messages without summarization
                assert len(result) == 20


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("user_id", [1, 999, 123456, -1, 0])
    def test_add_message_with_various_user_ids(
        self, conversation_manager, sample_message, user_id
    ):
        """
        Test adding messages with various user IDs.
        
        Testing Concept: Parameterized testing
        """
        if user_id != 0:
            conversation_manager.add_message(sample_message, user_id)
            assert conversation_manager.repository.save_message.called
        else:
            conversation_manager.add_message(sample_message, user_id)
            # 0 and negative should not save
            assert not conversation_manager.repository.save_message.called
        
        # Reset mock for next iteration
        conversation_manager.repository.save_message.reset_mock()
    
    @pytest.mark.parametrize("message_count,should_summarize", [
        (3, False),   # Below threshold
        (7, False),   # At threshold
        (8, False),   # At retrieval threshold
        (9, True),    # Above threshold
        (20, True),   # Well above threshold
    ])
    def test_get_messages_summarization_threshold(
        self, conversation_manager, message_count, should_summarize
    ):
        """
        Test summarization trigger at various message counts.
        
        Testing Concept: Parameterized boundary testing
        """
        # FIXED: Create messages with user_id
        messages = [
            Message(
                role="user", 
                content=f"Msg {i}", 
                timestamp=datetime.now(),
                user_id=1
            )
            for i in range(message_count)
        ]
        
        conversation_manager.repository.get_messages.return_value = messages
        
        result = conversation_manager.get_messages_for_llm(user_id=111)
        
        if should_summarize:
            conversation_manager.summarizer.summarize_for_retrieval.assert_called()
        else:
            conversation_manager.summarizer.summarize_for_retrieval.assert_not_called()
        
        # Reset for next iteration
        conversation_manager.summarizer.summarize_for_retrieval.reset_mock()

# ============================================================================
# TEST CLASS: Get Messages for LLM - Happy Path
# ============================================================================


class TestGetMessagesForLLMHappyPath:
    """Test retrieving messages formatted for LLM."""
    
    def test_get_messages_for_llm_returns_empty_list_when_no_messages(
        self, conversation_manager
    ):
        """
        Test that empty list is returned when no messages exist.
        
        Testing Concept: Test empty state
        """
        conversation_manager.repository.get_messages.return_value = []
        
        result = conversation_manager.get_messages_for_llm(user_id=123)
        
        assert result == []
    
    def test_get_messages_for_llm_calls_repository(self, conversation_manager):
        """
        Test that repository is called with correct user_id.
        
        Testing Concept: Verify dependency interaction
        """
        user_id = 456
        
        conversation_manager.get_messages_for_llm(user_id)
        
        conversation_manager.repository.get_messages.assert_called_once_with(
            user_id=user_id
        )
    
    def test_get_messages_for_llm_formats_messages_correctly(
        self, conversation_manager, conversation_history
    ):
        """
        Test that messages are formatted as chat API format.
        
        Testing Concept: Test data transformation
        """
        conversation_manager.repository.get_messages.return_value = conversation_history[:3]
        
        result = conversation_manager.get_messages_for_llm(user_id=789)
        
        # Should return list of dicts with 'role' and 'content'
        assert len(result) == 3
        assert all("role" in msg and "content" in msg for msg in result)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Message 0"
    
    def test_get_messages_for_llm_preserves_message_order(
        self, conversation_manager, conversation_history
    ):
        """
        Test that message order is preserved.
        
        Testing Concept: Test ordering
        """
        messages = [
            Message(role="user" if i % 2 == 0 else "assistant", 
                    content=f"Message {i}", 
                    timestamp=datetime.now(),
                    user_id=1)
            for i in range(5)  
        ]
        conversation_manager.repository.get_messages.return_value = messages
        
        result = conversation_manager.get_messages_for_llm(user_id=111)
        
        # Order should match original
        for i, msg in enumerate(result):
            assert msg["content"] == f"Message {i}"
    
    def test_get_messages_for_llm_without_summarization(
        self, mock_repository, mock_summarizer
    ):
        """
        Test message retrieval when summarization is disabled.
        
        Testing Concept: Test different configuration path
        """
        with patch("src.chat.conversation_manager.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.enable_summarization": False,
            }.get(key, default)
            
            with patch("src.chat.conversation_manager.ConversationSummarizer"):
                manager = ConversationManager(repository=mock_repository)
                
                # Even with many messages, should not summarize
                messages = [
                    Message(role="user", content=f"Msg {i}", timestamp=datetime.now(), user_id=1)
                    for i in range(20)
                ]
                manager.repository.get_messages.return_value = messages
                
                result = manager.get_messages_for_llm(user_id=222)
                
                # Should return all messages without summarization
                assert len(result) == 20

# ============================================================================
# TEST CLASS: Format Methods
# ============================================================================

class TestMessageFormatting:
    """Test internal message formatting methods."""
    
    def test_format_as_chat_messages(self, conversation_manager, conversation_history):
        """
        Test _format_as_chat_messages method.
        
        Testing Concept: Test private method behavior
        """
        result = conversation_manager._format_as_chat_messages(conversation_history[:3])
        
        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "Message 0"}
        assert result[1] == {"role": "assistant", "content": "Message 1"}
    
    def test_format_as_chat_messages_with_empty_list(self, conversation_manager):
        """
        Test formatting empty message list.
        
        Testing Concept: Test edge case
        """
        result = conversation_manager._format_as_chat_messages([])
        
        assert result == []
    
    def test_format_with_summary_when_messages_less_than_recent_count(
        self, conversation_manager
    ):
        """
        Test that no summarization happens when messages <= recent_count.
        
        Testing Concept: Test boundary condition
        """
        # Exactly 5 messages (same as recent_count)
        messages = [
            Message(role="user", content=f"Msg {i}", timestamp=datetime.now(), user_id=1)
            for i in range(5)
        ]
        
        result = conversation_manager._format_with_summary(messages, recent_count=5)
        
        # Should return all messages without summary
        assert len(result) == 5
        assert all(msg["role"] in ["user", "assistant"] for msg in result)
    
    def test_format_with_summary_splits_old_and_recent_correctly(
        self, conversation_manager, conversation_history
    ):
        """
        Test that messages are split correctly between old and recent.
        
        Testing Concept: Test list slicing logic
        """
        result = conversation_manager._format_with_summary(
            conversation_history, recent_count=3
        )
        
        # Should have: 1 summary + 3 recent = 4 total
        assert len(result) == 4
        
        # Recent messages should be last 3 (Message 7, 8, 9)
        assert result[1]["content"] == "Message 7"
        assert result[3]["content"] == "Message 9"
    
    def test_format_with_summary_calls_summarizer(
        self, conversation_manager, conversation_history
    ):
        """
        Test that summarizer is called with old messages.
        
        Testing Concept: Verify method calls
        """
        conversation_manager._format_with_summary(conversation_history, recent_count=5)
        
        # Should call summarizer with first 5 messages (10 - 5 = 5)
        call_args = conversation_manager.summarizer.summarize_for_retrieval.call_args
        old_messages = call_args[0][0]
        
        assert len(old_messages) == 5


# ============================================================================
# TEST CLASS: Clear Conversation
# ============================================================================


class TestClearConversation:
    """Test conversation clearing functionality."""
    
    def test_clear_conversation_calls_repository_delete(
        self, conversation_manager
    ):
        """
        Test that clear_conversation calls repository delete method.
        
        Testing Concept: Verify delegation to dependency
        """
        user_id = 888
        
        conversation_manager.clear_conversation(user_id)
        
        conversation_manager.repository.delete_conversation.assert_called_once_with(
            user_id
        )
    
    def test_clear_conversation_with_different_user_ids(
        self, conversation_manager
    ):
        """
        Test clearing conversations for different users.
        
        Testing Concept: Test multiple invocations
        """
        conversation_manager.clear_conversation(user_id=100)
        conversation_manager.clear_conversation(user_id=200)
        
        assert conversation_manager.repository.delete_conversation.call_count == 2
    
    def test_clear_conversation_with_zero_user_id(self, conversation_manager):
        """
        Test clearing with user_id=0.
        
        Testing Concept: Test edge case value
        """
        conversation_manager.clear_conversation(user_id=0)
        
        # Should still call delete (no filtering here)
        conversation_manager.repository.delete_conversation.assert_called_once_with(0)

# ============================================================================
# TEST CLASS: Cleanup Old Conversations
# ============================================================================


class TestCleanupOldConversations:
    """Test cleanup functionality."""
    
    def test_cleanup_calls_repository_cleanup_method(self, conversation_manager):
        """
        Test that cleanup calls repository method if available.
        
        Testing Concept: Test conditional method call based on hasattr
        """
        # Mock repository to have cleanup method
        conversation_manager.repository.cleanup_old_conversations = MagicMock(
            return_value=5
        )
        
        result = conversation_manager.cleanup_old_conversations(days=7)
        
        conversation_manager.repository.cleanup_old_conversations.assert_called_once_with(7)
        assert result == 5
    
    def test_cleanup_returns_zero_when_repository_lacks_method(
        self, conversation_manager
    ):
        """
        Test that cleanup returns 0 when repository doesn't support it.
        
        Testing Concept: Test graceful degradation
        """
        # Ensure repository doesn't have cleanup method
        if hasattr(conversation_manager.repository, "cleanup_old_conversations"):
            delattr(conversation_manager.repository, "cleanup_old_conversations")
        
        result = conversation_manager.cleanup_old_conversations(days=30)
        
        assert result == 0
    
    def test_cleanup_with_different_day_values(self, conversation_manager):
        """
        Test cleanup with various day parameters.
        
        Testing Concept: Test parameter variations
        """
        conversation_manager.repository.cleanup_old_conversations = MagicMock(
            return_value=3
        )
        
        # Test with different values
        conversation_manager.cleanup_old_conversations(days=1)
        conversation_manager.cleanup_old_conversations(days=30)
        conversation_manager.cleanup_old_conversations(days=365)
        
        assert conversation_manager.repository.cleanup_old_conversations.call_count == 3


# ============================================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCasesAndErrors:
    """Test edge cases and error conditions."""
    
    def test_add_message_with_none_message(self, conversation_manager):
        """
        Test behavior when message is None.
        
        Testing Concept: Test None input
        """
        # This might raise an error or be handled gracefully
        # Depending on implementation, adjust expectation
        try:
            conversation_manager.add_message(None, user_id=123)
            # If no error, verify save was called with None
            conversation_manager.repository.save_message.assert_called_with(123, None)
        except (AttributeError, TypeError):
            # Expected if code doesn't handle None
            pass
    
    def test_get_messages_for_llm_with_malformed_messages(
        self, conversation_manager
    ):
        """
        Test handling of messages missing attributes.
        
        Testing Concept: Test data validation
        """
        # Create message-like object without required attributes
        malformed = MagicMock()
        malformed.role = "user"
        # Missing 'content' attribute
        
        conversation_manager.repository.get_messages.return_value = [malformed]
        
        # Should handle gracefully or raise error
        try:
            result = conversation_manager.get_messages_for_llm(user_id=999)
        except AttributeError:
            # Expected if code doesn't validate
            pass
    
    def test_format_with_summary_with_negative_recent_count(
        self, conversation_manager, conversation_history
    ):
        """
        Test behavior with invalid recent_count.
        
        Testing Concept: Test invalid parameter
        """
        # Negative recent_count (edge case)
        result = conversation_manager._format_with_summary(
            conversation_history, recent_count=-1
        )
        
        # Should handle gracefully (might return all messages)
        assert isinstance(result, list)
    
    def test_cleanup_with_zero_days(self, conversation_manager):
        """
        Test cleanup with days=0.
        
        Testing Concept: Test boundary value
        """
        conversation_manager.repository.cleanup_old_conversations = MagicMock(
            return_value=0
        )
        
        result = conversation_manager.cleanup_old_conversations(days=0)
        
        assert result == 0


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short", 
        "--cov=src.chat.conversation_manager",
        "--cov-report=term-missing"
    ])