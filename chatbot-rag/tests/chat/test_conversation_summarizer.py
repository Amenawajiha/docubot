"""
Comprehensive unit tests for ConversationSummarizer.

This test suite covers:
- Initialization and configuration
- Summarization for storage (database compression)
- Summarization for retrieval (LLM context reduction)
- Message formatting
- Edge cases (empty lists, single messages, boundary conditions)
- LLM orchestrator integration
- Error handling
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.chat.conversation_summarizer import ConversationSummarizer
from src.models import Message


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """
    Mock configuration values.
    
    Testing Concept: Mock configuration loading
    """
    config_values = {
        "conversation.recent_count": 5,
        "conversation.storage_threshold": 50,
        "conversation.retrieval_threshold": 20,
    }
    
    with patch("src.chat.conversation_summarizer.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def mock_llm_orchestrator():
    """
    Mock LLM orchestrator.
    
    Testing Concept: Mock external LLM API calls
    """
    mock_orchestrator = MagicMock()
    
    # Mock send_message to return a summary and empty metadata
    mock_orchestrator.send_message = MagicMock(
        return_value=("This is a concise summary of the conversation.", {})
    )
    
    return mock_orchestrator


@pytest.fixture
def conversation_summarizer(mock_config, mock_llm_orchestrator):
    """
    Create ConversationSummarizer with mocked dependencies.
    
    Testing Concept: Fixture with dependency injection
    """
    with patch("src.chat.conversation_summarizer.LLMOrchestrator") as mock_llm_class:
        mock_llm_class.return_value = mock_llm_orchestrator
        
        summarizer = ConversationSummarizer()
        summarizer.llm_orchestrator = mock_llm_orchestrator
        
        return summarizer


@pytest.fixture
def sample_messages():
    """
    Create sample messages for testing.
    
    Testing Concept: Fixture providing test data
    """
    messages = []
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    for i in range(10):
        messages.append(
            Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message content {i}",
                timestamp=base_time,
                user_id=123,
                metadata={}
            )
        )
    
    return messages


@pytest.fixture
def large_message_set():
    """
    Create a large set of messages for threshold testing.
    
    Testing Concept: Fixture for boundary testing
    """
    messages = []
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    for i in range(50):
        messages.append(
            Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=base_time,
                user_id=456,
                metadata={}
            )
        )
    
    return messages


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestConversationSummarizerInitialization:
    """Test ConversationSummarizer initialization."""
    
    def test_initialization_creates_llm_orchestrator(self, mock_config):
        """
        Test that LLM orchestrator is initialized.
        
        Testing Concept: Verify dependency creation
        """
        with patch("src.chat.conversation_summarizer.LLMOrchestrator") as mock_llm:
            summarizer = ConversationSummarizer()
            
            mock_llm.assert_called_once()
            assert summarizer.llm_orchestrator is not None
    
    def test_initialization_loads_recent_count_from_config(self):
        """
        Test that recent_count is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.chat.conversation_summarizer.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "conversation.recent_count": 7,
            }.get(key, default)
            
            with patch("src.chat.conversation_summarizer.LLMOrchestrator"):
                summarizer = ConversationSummarizer()
                
                # Access private attribute for testing
                assert summarizer._ConversationSummarizer__recent_count == 7
    
    def test_initialization_with_default_recent_count(self, mock_config):
        """
        Test initialization with default recent count.
        
        Testing Concept: Test default configuration
        """
        with patch("src.chat.conversation_summarizer.LLMOrchestrator"):
            summarizer = ConversationSummarizer()
            
            assert summarizer._ConversationSummarizer__recent_count == 5


# ============================================================================
# TEST CLASS: Summarize for Storage - Happy Path
# ============================================================================


class TestSummarizeForStorageHappyPath:
    """Test successful summarization for storage scenarios."""
    
    def test_summarize_for_storage_returns_message_object(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that summarize_for_storage returns a Message object.
        
        Testing Concept: Test return type
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert isinstance(result, Message)
    
    def test_summarize_for_storage_calls_llm_orchestrator(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that LLM orchestrator is called with correct prompt.
        
        Testing Concept: Verify dependency interaction
        """
        conversation_summarizer.summarize_for_storage(sample_messages)
        
        # Verify send_message was called
        conversation_summarizer.llm_orchestrator.send_message.assert_called_once()
        
        # Verify prompt contains conversation text
        call_args = conversation_summarizer.llm_orchestrator.send_message.call_args
        prompt = call_args[0][0]
        
        assert "Message content 0" in prompt or "user:" in prompt.lower()
    
    def test_summarize_for_storage_message_has_correct_role(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that summary message has 'assistant' role.
        
        Testing Concept: Test data attributes
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert result.role == "assistant"
    
    def test_summarize_for_storage_content_includes_summary_prefix(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that summary content has identifying prefix.
        
        Testing Concept: Test output format
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert result.content.startswith("[Summary of previous conversation]:")
    
    def test_summarize_for_storage_includes_llm_summary(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that LLM-generated summary is included in message.
        
        Testing Concept: Test data transformation
        """
        # Mock LLM to return specific summary
        conversation_summarizer.llm_orchestrator.send_message.return_value = (
            "Custom summary text", {}
        )
        
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert "Custom summary text" in result.content
    
    def test_summarize_for_storage_sets_user_id_from_first_message(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that user_id is copied from first message.
        
        Testing Concept: Test attribute propagation
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert result.user_id == sample_messages[0].user_id
        assert result.user_id == 123
    
    def test_summarize_for_storage_has_timezone_aware_timestamp(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that timestamp is timezone-aware UTC.
        
        Testing Concept: Test timezone handling
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert result.timestamp.tzinfo is not None
        assert result.timestamp.tzinfo == timezone.utc
    
    def test_summarize_for_storage_metadata_indicates_summary(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that metadata marks message as summary.
        
        Testing Concept: Test metadata attributes
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert result.metadata["is_summary"] is True
    
    def test_summarize_for_storage_metadata_includes_count(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that metadata includes count of summarized messages.
        
        Testing Concept: Test metadata completeness
        """
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        assert result.metadata["summarized_count"] == len(sample_messages)
        assert result.metadata["summarized_count"] == 10
    
    def test_summarize_for_storage_with_different_message_counts(
        self, conversation_summarizer
    ):
        """
        Test summarization with various message counts.
        
        Testing Concept: Test scalability
        """
        for count in [1, 5, 20, 100]:
            messages = [
                Message(
                    role="user",
                    content=f"Msg {i}",
                    timestamp=datetime.now(timezone.utc),
                    user_id=999,
                    metadata={}
                )
                for i in range(count)
            ]
            
            result = conversation_summarizer.summarize_for_storage(messages)
            
            assert result.metadata["summarized_count"] == count
    
    def test_summarize_for_storage_formats_conversation_text_correctly(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that conversation text is formatted correctly for LLM.
        
        Testing Concept: Test data formatting
        """
        conversation_summarizer.summarize_for_storage(sample_messages)
        
        call_args = conversation_summarizer.llm_orchestrator.send_message.call_args
        prompt = call_args[0][0]
        
        # Should contain role and content in format "role: content"
        assert "user: Message content 0" in prompt or "user:" in prompt.lower()
        assert "assistant:" in prompt.lower()


# ============================================================================
# TEST CLASS: Summarize for Storage - Edge Cases
# ============================================================================


class TestSummarizeForStorageEdgeCases:
    """Test edge cases for storage summarization."""
    
    def test_summarize_for_storage_with_single_message(
        self, conversation_summarizer
    ):
        """
        Test summarizing a single message.
        
        Testing Concept: Test minimum input
        """
        single_message = [
            Message(
                role="user",
                content="Single message",
                timestamp=datetime.now(timezone.utc),
                user_id=111,
                metadata={}
            )
        ]
        
        result = conversation_summarizer.summarize_for_storage(single_message)
        
        assert result.metadata["summarized_count"] == 1
        assert result.user_id == 111
    
    def test_summarize_for_storage_with_empty_list(
        self, conversation_summarizer
    ):
        """
        Test behavior with empty message list.
        
        Testing Concept: Test empty input
        """
        empty_list = []
        
        result = conversation_summarizer.summarize_for_storage(empty_list)
        
        # Should handle gracefully
        assert result.metadata["summarized_count"] == 0
        assert result.user_id == 0  # Default system user ID
    
    def test_summarize_for_storage_with_messages_without_user_id(
        self, conversation_summarizer
    ):
        """
        Test handling messages without user_id.
        
        Testing Concept: Test that Pydantic validates required fields
        Note: user_id is REQUIRED by Pydantic, so this test verifies validation works
        """
        # Pydantic should raise ValidationError if user_id is missing
        from pydantic_core import ValidationError
        
        with pytest.raises(ValidationError, match="user_id"):
            Message(
                role="user",
                content="Test",
                timestamp=datetime.now(timezone.utc),
                metadata={}
                # Missing user_id - should raise ValidationError
            )
    
    def test_summarize_for_storage_with_long_messages(
        self, conversation_summarizer
    ):
        """
        Test summarizing very long messages.
        
        Testing Concept: Test large input
        """
        long_messages = [
            Message(
                role="user",
                content="A" * 1000,  # Very long content
                timestamp=datetime.now(timezone.utc),
                user_id=222,
                metadata={}
            )
            for _ in range(10)
        ]
        
        result = conversation_summarizer.summarize_for_storage(long_messages)
        
        assert result.metadata["summarized_count"] == 10
    
    def test_summarize_for_storage_strips_whitespace_from_summary(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that summary content is stripped of extra whitespace.
        
        Testing Concept: Test data cleaning
        """
        # Mock LLM to return summary with whitespace
        conversation_summarizer.llm_orchestrator.send_message.return_value = (
            "  Summary with whitespace  \n", {}
        )
        
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        # Should be stripped
        assert not result.content.endswith("  ")
        assert "Summary with whitespace" in result.content


# ============================================================================
# TEST CLASS: Summarize for Retrieval - Happy Path
# ============================================================================


class TestSummarizeForRetrievalHappyPath:
    """Test successful summarization for retrieval scenarios."""
    
    def test_summarize_for_retrieval_returns_string(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that summarize_for_retrieval returns a string.
        
        Testing Concept: Test return type
        """
        result = conversation_summarizer.summarize_for_retrieval(sample_messages)
        
        assert isinstance(result, str)
    
    def test_summarize_for_retrieval_calls_llm_when_above_threshold(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test that LLM is called when message count exceeds threshold.
        
        Testing Concept: Test conditional LLM invocation
        """
        result = conversation_summarizer.summarize_for_retrieval(large_message_set)
        
        # Should call LLM for summarization
        conversation_summarizer.llm_orchestrator.send_message.assert_called_once()
    
    def test_summarize_for_retrieval_does_not_call_llm_below_threshold(
        self, conversation_summarizer
    ):
        """
        Test that LLM is not called for small message lists.
        
        Testing Concept: Test early return optimization
        """
        few_messages = [
            Message(
                role="user",
                content=f"Msg {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=333,
                metadata={}
            )
            for i in range(3)  # Below threshold of 5
        ]
        
        result = conversation_summarizer.summarize_for_retrieval(few_messages)
        
        # Should not call LLM (returns all messages formatted)
        conversation_summarizer.llm_orchestrator.send_message.assert_not_called()
        
        # Should return formatted messages
        assert "Msg 0" in result
        assert "Msg 2" in result
    
    def test_summarize_for_retrieval_at_threshold_boundary(
        self, conversation_summarizer
    ):
        """
        Test behavior exactly at threshold (5 messages).
        
        Testing Concept: Test boundary condition
        """
        exactly_threshold = [
            Message(
                role="user",
                content=f"Msg {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=444,
                metadata={}
            )
            for i in range(5)  # Exactly at threshold
        ]
        
        result = conversation_summarizer.summarize_for_retrieval(exactly_threshold)
        
        # At threshold, should not summarize (<=)
        conversation_summarizer.llm_orchestrator.send_message.assert_not_called()
    
    def test_summarize_for_retrieval_includes_summary_prefix(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test that output includes summary prefix.
        
        Testing Concept: Test output format
        """
        result = conversation_summarizer.summarize_for_retrieval(large_message_set)
        
        assert "Previous conversation summary:" in result
    
    def test_summarize_for_retrieval_includes_recent_conversation_section(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test that output includes recent conversation section.
        
        Testing Concept: Test output structure
        """
        result = conversation_summarizer.summarize_for_retrieval(large_message_set)
        
        assert "Recent conversation:" in result
    
    def test_summarize_for_retrieval_includes_llm_summary(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test that LLM-generated summary is included.
        
        Testing Concept: Test data integration
        """
        # Mock LLM to return specific summary
        conversation_summarizer.llm_orchestrator.send_message.return_value = (
            "Custom retrieval summary", {}
        )
        
        result = conversation_summarizer.summarize_for_retrieval(large_message_set)
        
        assert "Custom retrieval summary" in result
    
    def test_summarize_for_retrieval_includes_last_n_messages(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test that last N messages are included in full.
        
        Testing Concept: Test data slicing
        """
        result = conversation_summarizer.summarize_for_retrieval(large_message_set)
        
        # Should include last 5 messages (45-49)
        assert "Message 45" in result
        assert "Message 49" in result
    
    def test_summarize_for_retrieval_does_not_include_old_messages_in_full(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test that old messages are not included in full detail.
        
        Testing Concept: Test data exclusion
        """
        result = conversation_summarizer.summarize_for_retrieval(large_message_set)
        
        # Should NOT include early messages in full (only in summary)
        # Message 0-44 should be summarized, not present verbatim
        # This is hard to test definitively, but we can check structure
        assert "Recent conversation:" in result
        
        # Old messages should not appear after "Recent conversation:"
        recent_section = result.split("Recent conversation:")[1]
        assert "Message 0" not in recent_section
    
    def test_summarize_for_retrieval_splits_messages_correctly(
        self, conversation_summarizer
    ):
        """
        Test that messages are split into old and recent correctly.
        
        Testing Concept: Test list slicing logic
        """
        # Create exactly 10 messages
        ten_messages = [
            Message(
                role="user",
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=555,
                metadata={}
            )
            for i in range(10)
        ]
        
        result = conversation_summarizer.summarize_for_retrieval(ten_messages)
        
        # Should summarize first 5, keep last 5
        # Last 5 are messages 5-9
        assert "Message 5" in result
        assert "Message 9" in result


# ============================================================================
# TEST CLASS: Summarize for Retrieval - Edge Cases
# ============================================================================


class TestSummarizeForRetrievalEdgeCases:
    """Test edge cases for retrieval summarization."""
    
    def test_summarize_for_retrieval_with_empty_list(
        self, conversation_summarizer
    ):
        """
        Test with empty message list.
        
        Testing Concept: Test empty input
        """
        empty_list = []
        
        result = conversation_summarizer.summarize_for_retrieval(empty_list)
        
        # Should return empty string or minimal formatting
        assert isinstance(result, str)
        assert len(result) == 0 or result.strip() == ""
    
    def test_summarize_for_retrieval_with_one_message(
        self, conversation_summarizer
    ):
        """
        Test with single message.
        
        Testing Concept: Test minimum valid input
        """
        single_message = [
            Message(
                role="user",
                content="Only message",
                timestamp=datetime.now(timezone.utc),
                user_id=666,
                metadata={}
            )
        ]
        
        result = conversation_summarizer.summarize_for_retrieval(single_message)
        
        # Should not summarize (below threshold)
        conversation_summarizer.llm_orchestrator.send_message.assert_not_called()
        assert "Only message" in result
    
    def test_summarize_for_retrieval_with_exactly_recent_count_plus_one(
        self, conversation_summarizer
    ):
        """
        Test with exactly threshold + 1 messages (6 messages).
        
        Testing Concept: Test boundary + 1
        """
        six_messages = [
            Message(
                role="user",
                content=f"Msg {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=777,
                metadata={}
            )
            for i in range(6)
        ]
        
        result = conversation_summarizer.summarize_for_retrieval(six_messages)
        
        # Should trigger summarization (6 > 5)
        conversation_summarizer.llm_orchestrator.send_message.assert_called_once()
        
        # Should summarize first 1, keep last 5
        assert "Msg 1" in result
        assert "Msg 5" in result


# ============================================================================
# TEST CLASS: Format Messages Helper
# ============================================================================


class TestFormatMessagesHelper:
    """Test _format_messages private method."""
    
    def test_format_messages_returns_string(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that _format_messages returns a string.
        
        Testing Concept: Test return type
        """
        result = conversation_summarizer._format_messages(sample_messages[:3])
        
        assert isinstance(result, str)
    
    def test_format_messages_includes_all_messages(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that all messages are included in output.
        
        Testing Concept: Test data completeness
        """
        result = conversation_summarizer._format_messages(sample_messages[:5])
        
        # Should include all 5 messages
        for i in range(5):
            assert f"Message content {i}" in result
    
    def test_format_messages_uses_correct_format(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that format is "role: content".
        
        Testing Concept: Test output format
        """
        result = conversation_summarizer._format_messages(sample_messages[:2])
        
        # Should have format "role: content"
        assert "user: Message content 0" in result
        assert "assistant: Message content 1" in result
    
    def test_format_messages_separates_with_newlines(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that messages are separated by newlines.
        
        Testing Concept: Test delimiter
        """
        result = conversation_summarizer._format_messages(sample_messages[:3])
        
        # Should contain newlines between messages
        lines = result.split("\n")
        assert len(lines) == 3
    
    def test_format_messages_with_empty_list(
        self, conversation_summarizer
    ):
        """
        Test formatting empty message list.
        
        Testing Concept: Test empty input
        """
        result = conversation_summarizer._format_messages([])
        
        assert result == ""
    
    def test_format_messages_with_single_message(
        self, conversation_summarizer
    ):
        """
        Test formatting single message.
        
        Testing Concept: Test single item
        """
        single = [
            Message(
                role="user",
                content="Single",
                timestamp=datetime.now(timezone.utc),
                user_id=888,
                metadata={}
            )
        ]
        
        result = conversation_summarizer._format_messages(single)
        
        assert result == "user: Single"
    
    def test_format_messages_preserves_message_order(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that message order is preserved.
        
        Testing Concept: Test ordering
        """
        result = conversation_summarizer._format_messages(sample_messages)
        
        lines = result.split("\n")
        
        # Check order
        for i in range(len(sample_messages)):
            assert f"Message content {i}" in lines[i]


# ============================================================================
# TEST CLASS: LLM Integration and Error Handling
# ============================================================================


class TestLLMIntegrationAndErrors:
    """Test LLM orchestrator integration and error scenarios."""
    
    def test_summarize_handles_llm_returning_empty_string(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test handling when LLM returns empty summary.
        
        Testing Concept: Test edge case response
        """
        # Mock LLM to return empty string
        conversation_summarizer.llm_orchestrator.send_message.return_value = ("", {})
        
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        # Should still create valid message
        assert isinstance(result, Message)
        assert "[Summary of previous conversation]:" in result.content
    
    def test_summarize_handles_llm_returning_whitespace(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test handling when LLM returns only whitespace.
        
        Testing Concept: Test malformed response
        """
        conversation_summarizer.llm_orchestrator.send_message.return_value = (
            "   \n\t  ", {}
        )
        
        result = conversation_summarizer.summarize_for_storage(sample_messages)
        
        # Should strip whitespace
        assert result.content.strip().endswith(":")  # Empty after stripping
    
    def test_summarize_for_storage_with_llm_exception(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test behavior when LLM raises exception.
        
        Testing Concept: Test error handling
        """
        # Mock LLM to raise exception
        conversation_summarizer.llm_orchestrator.send_message.side_effect = Exception(
            "LLM API error"
        )
        
        # Should raise exception (or handle gracefully depending on implementation)
        with pytest.raises(Exception, match="LLM API error"):
            conversation_summarizer.summarize_for_storage(sample_messages)
    
    def test_summarize_for_retrieval_with_llm_exception(
        self, conversation_summarizer, large_message_set
    ):
        """
        Test retrieval summarization when LLM fails.
        
        Testing Concept: Test error propagation
        """
        conversation_summarizer.llm_orchestrator.send_message.side_effect = Exception(
            "LLM timeout"
        )
        
        with pytest.raises(Exception, match="LLM timeout"):
            conversation_summarizer.summarize_for_retrieval(large_message_set)
    
    def test_summarize_verifies_prompt_format(
        self, conversation_summarizer, sample_messages
    ):
        """
        Test that prompt is properly formatted before sending to LLM.
        
        Testing Concept: Test data validation
        """
        conversation_summarizer.summarize_for_storage(sample_messages)
        
        call_args = conversation_summarizer.llm_orchestrator.send_message.call_args
        prompt = call_args[0][0]
        
        # Should be a non-empty string
        assert isinstance(prompt, str)
        assert len(prompt) > 0


# ============================================================================
# TEST CLASS: Integration and Complex Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_storage_summarization_workflow(
        self, conversation_summarizer
    ):
        """
        Test complete workflow for storage summarization.
        
        Testing Concept: Integration test
        """
        # Create conversation history
        messages = [
            Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Turn {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=12345,
                metadata={}
            )
            for i in range(45)  # Old messages to summarize
        ]
        
        # Summarize
        summary = conversation_summarizer.summarize_for_storage(messages)
        
        # Verify result
        assert summary.role == "assistant"
        assert summary.user_id == 12345
        assert summary.metadata["is_summary"] is True
        assert summary.metadata["summarized_count"] == 45
        assert "[Summary of previous conversation]:" in summary.content
    
    def test_full_retrieval_summarization_workflow(
        self, conversation_summarizer
    ):
        """
        Test complete workflow for retrieval summarization.
        
        Testing Concept: Integration test
        """
        # Create large conversation
        messages = [
            Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Exchange {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=54321,
                metadata={}
            )
            for i in range(30)  # Above threshold
        ]
        
        # Summarize for retrieval
        context = conversation_summarizer.summarize_for_retrieval(messages)
        
        # Verify structure
        assert "Previous conversation summary:" in context
        assert "Recent conversation:" in context
        
        # Should include recent messages (25-29)
        assert "Exchange 25" in context
        assert "Exchange 29" in context
    
    def test_mixed_roles_in_conversation(
        self, conversation_summarizer
    ):
        """
        Test handling conversation with multiple role types.
        
        Testing Concept: Test data variety
        """
        mixed_messages = [
            Message(role="user", content="Q1", timestamp=datetime.now(timezone.utc), user_id=1, metadata={}),
            Message(role="assistant", content="A1", timestamp=datetime.now(timezone.utc), user_id=1, metadata={}),
            Message(role="user", content="Q2", timestamp=datetime.now(timezone.utc), user_id=1, metadata={}),
            Message(role="assistant", content="A2", timestamp=datetime.now(timezone.utc), user_id=1, metadata={}),
        ]
        
        result = conversation_summarizer.summarize_for_storage(mixed_messages)
        
        assert result.metadata["summarized_count"] == 4
    
    def test_summarization_with_different_user_ids(
        self, conversation_summarizer
    ):
        """
        Test that summarization preserves user_id from first message.
        
        Testing Concept: Test attribute preservation across messages
        """
        messages = [
            Message(role="user", content=f"Msg {i}", timestamp=datetime.now(timezone.utc), user_id=999, metadata={})
            for i in range(10)
        ]
        
        summary = conversation_summarizer.summarize_for_storage(messages)
        
        assert summary.user_id == 999


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("message_count,should_summarize", [
        (1, False),   # Below threshold
        (3, False),   # Below threshold
        (5, False),   # At threshold
        (6, True),    # Above threshold
        (10, True),   # Above threshold
        (50, True),   # Well above threshold
    ])
    def test_summarize_for_retrieval_threshold_behavior(
        self, conversation_summarizer, message_count, should_summarize
    ):
        """
        Test summarization threshold with various message counts.
        
        Testing Concept: Parameterized boundary testing
        """
        messages = [
            Message(
                role="user",
                content=f"Msg {i}",
                timestamp=datetime.now(timezone.utc),
                user_id=111,
                metadata={}
            )
            for i in range(message_count)
        ]
        
        result = conversation_summarizer.summarize_for_retrieval(messages)
        
        if should_summarize:
            conversation_summarizer.llm_orchestrator.send_message.assert_called()
        else:
            conversation_summarizer.llm_orchestrator.send_message.assert_not_called()
        
        # Reset for next iteration
        conversation_summarizer.llm_orchestrator.send_message.reset_mock()
    
    @pytest.mark.parametrize("role", ["user", "assistant"])
    def test_format_messages_with_different_roles(
        self, conversation_summarizer, role
    ):
        """
        Test formatting messages with different roles.
        
        Testing Concept: Parameterized role testing
        """
        message = [
            Message(
                role=role,
                content="Test content",
                timestamp=datetime.now(timezone.utc),
                user_id=222,
                metadata={}
            )
        ]
        
        result = conversation_summarizer._format_messages(message)
        
        assert f"{role}: Test content" in result


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.chat.conversation_summarizer",
        "--cov-report=term-missing"
    ])


