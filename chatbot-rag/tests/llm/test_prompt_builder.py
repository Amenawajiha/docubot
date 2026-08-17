"""
Comprehensive unit tests for PromptBuilder.

This test suite covers:
- Context formatting (format_context)
- User message building (build_user_message)
- User message with history (build_user_message_with_history)
- Clarification messages (build_clarification_messages)
- User conversation messages (build_user_conversation_messages)
- Edge cases and error handling
- Branch coverage for all conditional logic
"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.llm.prompt_builder import PromptBuilder
from src.models import RetrievalResult


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def prompt_builder():
    """
    Create PromptBuilder instance.
    
    Testing Concept: Basic fixture
    """
    return PromptBuilder()


@pytest.fixture
def mock_logger():
    """
    Mock logger to avoid actual logging during tests.
    
    Testing Concept: Mock logging
    """
    with patch("src.llm.prompt_builder.logger") as mock:
        yield mock


@pytest.fixture
def sample_retrieval_results_dict():
    """
    Sample retrieval results as dictionaries.
    
    Testing Concept: Fixture for dict-based data
    """
    return [
        {
            "content": "A Schengen visa allows travel to 27 European countries.",
            "metadata": {
                "document_name": "schengen_visa_guide.pdf",
                "chunk_type": "text",
                "page": 1
            },
            "relevance_score": 0.95
        },
        {
            "content": "You need a valid passport for Schengen visa application.",
            "metadata": {
                "document_name": "visa_requirements.pdf",
                "chunk_type": "text",
                "page": 3
            },
            "relevance_score": 0.87
        }
    ]


@pytest.fixture
def sample_retrieval_results_objects():
    """
    Sample retrieval results as Pydantic objects.
    
    Testing Concept: Fixture for object-based data
    """
    return [
        RetrievalResult(
            content="A Schengen visa allows travel to 27 European countries.",
            metadata={
                "document_name": "schengen_visa_guide.pdf",
                "chunk_type": "text",
                "page": 1
            },
            relevance_score=0.95
        ),
        RetrievalResult(
            content="You need a valid passport for Schengen visa application.",
            metadata={
                "document_name": "visa_requirements.pdf",
                "chunk_type": "text",
                "page": 3
            },
            relevance_score=0.87
        )
    ]


@pytest.fixture
def sample_conversation_history():
    """
    Sample conversation history.
    
    Testing Concept: Fixture for conversation context
    """
    return [
        {"role": "user", "content": "What is a Schengen visa?"},
        {"role": "assistant", "content": "A Schengen visa allows you to travel..."},
        {"role": "user", "content": "What documents do I need?"}
    ]


@pytest.fixture
def mock_prompts():
    """
    Mock prompt templates.
    
    Testing Concept: Mock constants
    """
    with patch("src.llm.prompt_builder.SYSTEM_PROMPT_TEMPLATE") as mock_system:
        with patch("src.llm.prompt_builder.QUERY_PROMPT") as mock_query:
            with patch("src.llm.prompt_builder.CONTACT_FALLBACK") as mock_contact:
                with patch("src.llm.prompt_builder.CLARIFICATION_SYSTEM_INSTRUCTION") as mock_clarif_sys:
                    with patch("src.llm.prompt_builder.CLARIFICATION_USER_TEMPLATE") as mock_clarif_user:
                        mock_system.format = MagicMock(return_value="System prompt with {current_date}")
                        mock_query.format = MagicMock(return_value="Query prompt")
                        mock_contact.return_value = "Contact fallback"
                        mock_clarif_sys.return_value = "Clarification system"
                        mock_clarif_user.format = MagicMock(return_value="Clarification user")
                        
                        yield {
                            "system": mock_system,
                            "query": mock_query,
                            "contact": mock_contact,
                            "clarif_sys": mock_clarif_sys,
                            "clarif_user": mock_clarif_user
                        }


# ============================================================================
# TEST CLASS: Format Context Tests
# ============================================================================


class TestFormatContext:
    """Test format_context functionality."""
    
    def test_format_context_with_dict_results(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test formatting context from dictionary results.
        
        Testing Concept: Happy path with dict input
        """
        result = prompt_builder.format_context(sample_retrieval_results_dict)
        
        assert isinstance(result, str)
        assert "schengen_visa_guide.pdf" in result
        assert "visa_requirements.pdf" in result
        assert "A Schengen visa allows travel" in result
        assert "valid passport" in result
        assert "0.95" in result
        assert "0.87" in result
    
    def test_format_context_with_object_results(
        self, prompt_builder, sample_retrieval_results_objects
    ):
        """
        Test formatting context from Pydantic object results.
        
        Testing Concept: Happy path with object input
        """
        result = prompt_builder.format_context(sample_retrieval_results_objects)
        
        assert isinstance(result, str)
        assert "schengen_visa_guide.pdf" in result
        assert "A Schengen visa allows travel" in result
        assert "Source:" in result
        assert "Type:" in result
        assert "Content:" in result
        assert "Relevance:" in result
    
    def test_format_context_with_empty_list(self, prompt_builder):
        """
        Test formatting context with empty results.
        
        Testing Concept: Test empty input
        """
        result = prompt_builder.format_context([])
        
        assert result == "NO_CONTEXT"
    
    def test_format_context_with_none_list(self, prompt_builder):
        """
        Test formatting context with None.
        
        Testing Concept: Test None input
        """
        result = prompt_builder.format_context(None)
        
        # Should handle None as falsy and return NO_CONTEXT
        assert result == "NO_CONTEXT"
    
    def test_format_context_with_single_result(self, prompt_builder):
        """
        Test formatting context with single result.
        
        Testing Concept: Test single iteration
        """
        single_result = [
            {
                "content": "Single document content",
                "metadata": {"document_name": "doc.pdf", "chunk_type": "text"},
                "relevance_score": 0.8
            }
        ]
        
        result = prompt_builder.format_context(single_result)
        
        assert "Single document content" in result
        assert "doc.pdf" in result
        assert "0.80" in result
    
    def test_format_context_with_many_results(self, prompt_builder):
        """
        Test formatting context with many results.
        
        Testing Concept: Test many iterations
        """
        many_results = [
            {
                "content": f"Content {i}",
                "metadata": {"document_name": f"doc{i}.pdf", "chunk_type": "text"},
                "relevance_score": 0.9 - (i * 0.1)
            }
            for i in range(10)
        ]
        
        result = prompt_builder.format_context(many_results)
        
        # Check all documents are included
        for i in range(10):
            assert f"doc{i}.pdf" in result
            assert f"Content {i}" in result
    
    def test_format_context_with_missing_metadata(self, prompt_builder):
        """
        Test formatting context when metadata is missing.
        
        Testing Concept: Test missing dict keys
        """
        result_missing_metadata = [
            {
                "content": "Some content",
                "relevance_score": 0.7
                # No metadata
            }
        ]
        
        result = prompt_builder.format_context(result_missing_metadata)
        
        # Should use defaults
        assert "Unknown" in result  # Default document_name
        assert "text" in result  # Default chunk_type
        assert "Some content" in result
    
    def test_format_context_with_partial_metadata(self, prompt_builder):
        """
        Test formatting context with partial metadata.
        
        Testing Concept: Test missing nested dict keys
        """
        result_partial_metadata = [
            {
                "content": "Content here",
                "metadata": {"document_name": "doc.pdf"},  # Missing chunk_type
                "relevance_score": 0.8
            }
        ]
        
        result = prompt_builder.format_context(result_partial_metadata)
        
        assert "doc.pdf" in result
        assert "text" in result  # Default chunk_type
    
    def test_format_context_with_mixed_types(self, prompt_builder):
        """
        Test formatting context with mixed dict and object types.
        
        Testing Concept: Test mixed input types
        """
        mixed_results = [
            {
                "content": "Dict content",
                "metadata": {"document_name": "dict_doc.pdf", "chunk_type": "text"},
                "relevance_score": 0.9
            },
            RetrievalResult(
                content="Object content",
                metadata={"document_name": "obj_doc.pdf", "chunk_type": "text"},
                relevance_score=0.85
            )
        ]
        
        result = prompt_builder.format_context(mixed_results)
        
        assert "dict_doc.pdf" in result
        assert "obj_doc.pdf" in result
        assert "Dict content" in result
        assert "Object content" in result
    
    def test_format_context_includes_all_fields(self, prompt_builder):
        """
        Test that all expected fields are included in output.
        
        Testing Concept: Test complete output structure
        """
        results = [
            {
                "content": "Test content",
                "metadata": {"document_name": "test.pdf", "chunk_type": "heading"},
                "relevance_score": 0.75
            }
        ]
        
        result = prompt_builder.format_context(results)
        
        # Check all expected fields
        assert "Source: test.pdf" in result
        assert "Type: heading" in result
        assert "Content: Test content" in result
        assert "Relevance: 0.75" in result
    
    def test_format_context_formats_relevance_score(self, prompt_builder):
        """
        Test that relevance score is formatted to 2 decimal places.
        
        Testing Concept: Test number formatting
        """
        results = [
            {
                "content": "Content",
                "metadata": {"document_name": "doc.pdf", "chunk_type": "text"},
                "relevance_score": 0.123456789
            }
        ]
        
        result = prompt_builder.format_context(results)
        
        assert "0.12" in result
        assert "0.123456" not in result


# ============================================================================
# TEST CLASS: Build User Message Tests
# ============================================================================


class TestBuildUserMessage:
    """Test build_user_message functionality."""
    
    def test_build_user_message_with_context(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test building user message with context.
        
        Testing Concept: Happy path with context
        """
        query = "What documents do I need for Schengen visa?"
        
        result = prompt_builder.build_user_message(query, sample_retrieval_results_dict)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_build_user_message_calls_format_context(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that format_context is called.
        
        Testing Concept: Verify method delegation
        """
        with patch.object(prompt_builder, 'format_context') as mock_format:
            mock_format.return_value = "Formatted context"
            
            prompt_builder.build_user_message("Query", sample_retrieval_results_dict)
            
            mock_format.assert_called_once_with(sample_retrieval_results_dict)
    
    def test_build_user_message_with_empty_context(self, prompt_builder):
        """
        Test building user message with empty context.
        
        Testing Concept: Test empty context
        """
        query = "What is AI?"
        
        result = prompt_builder.build_user_message(query, [])
        
        assert isinstance(result, str)
        assert "NO_CONTEXT" in result or len(result) > 0
    
    def test_build_user_message_with_empty_query(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test building user message with empty query.
        
        Testing Concept: Test empty query
        """
        result = prompt_builder.build_user_message("", sample_retrieval_results_dict)
        
        assert isinstance(result, str)
    
    def test_build_user_message_includes_contact_fallback(self, prompt_builder):
        """
        Test that contact fallback is included.
        
        Testing Concept: Test template usage
        """
        with patch("src.llm.prompt_builder.QUERY_PROMPT") as mock_query:
            with patch("src.llm.prompt_builder.CONTACT_FALLBACK", "Contact us at support@example.com"):
                mock_query.format = MagicMock(return_value="Formatted with contact")
                
                result = prompt_builder.build_user_message("Query", [])
                
                # Verify QUERY_PROMPT.format was called with contact_fallback
                mock_query.format.assert_called_once()
                call_kwargs = mock_query.format.call_args[1]
                assert "contact_fallback" in call_kwargs
    
    def test_build_user_message_with_special_characters(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with special characters in query.
        
        Testing Concept: Test special character handling
        """
        query = "What about émojis 🎉 and spëcial çhars?"
        
        result = prompt_builder.build_user_message(query, sample_retrieval_results_dict)
        
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS: Build User Message With History Tests
# ============================================================================


class TestBuildUserMessageWithHistory:
    """Test build_user_message_with_history functionality."""
    
    def test_build_user_message_with_history_returns_list(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that method returns a list of messages.
        
        Testing Concept: Test return type
        """
        result = prompt_builder.build_user_message_with_history(
            "New query", sample_retrieval_results_dict, sample_conversation_history
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(msg, dict) for msg in result)
    
    def test_build_user_message_with_history_includes_system_prompt(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that system prompt is first message.
        
        Testing Concept: Test message structure
        """
        result = prompt_builder.build_user_message_with_history(
            "Query", sample_retrieval_results_dict, sample_conversation_history
        )
        
        assert result[0]["role"] == "system"
        assert "content" in result[0]
        assert isinstance(result[0]["content"], str)
    
    def test_build_user_message_with_history_includes_history(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that conversation history is included.
        
        Testing Concept: Test history inclusion
        """
        result = prompt_builder.build_user_message_with_history(
            "New query", sample_retrieval_results_dict, sample_conversation_history
        )
        
        # Should have: system + history (3) + current query = 5 messages
        assert len(result) == 5
        
        # Verify history messages are present
        assert result[1] == sample_conversation_history[0]
        assert result[2] == sample_conversation_history[1]
        assert result[3] == sample_conversation_history[2]
    
    def test_build_user_message_with_history_appends_current_query(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that current query with context is last message.
        
        Testing Concept: Test message ordering
        """
        query = "What are the fees?"
        
        result = prompt_builder.build_user_message_with_history(
            query, sample_retrieval_results_dict, sample_conversation_history
        )
        
        # Last message should be current query
        assert result[-1]["role"] == "user"
        assert isinstance(result[-1]["content"], str)
    
    def test_build_user_message_with_history_without_history(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with None conversation history.
        
        Testing Concept: Test None optional parameter
        """
        result = prompt_builder.build_user_message_with_history(
            "Query", sample_retrieval_results_dict, None
        )
        
        # Should have: system + current query = 2 messages
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
    
    def test_build_user_message_with_history_with_empty_history(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with empty conversation history.
        
        Testing Concept: Test empty list parameter
        """
        result = prompt_builder.build_user_message_with_history(
            "Query", sample_retrieval_results_dict, []
        )
        
        # Should have: system + current query = 2 messages
        assert len(result) == 2
    
    def test_build_user_message_with_history_injects_current_date(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that current date is injected into system prompt.
        
        Testing Concept: Test date injection
        """
        with patch("src.llm.prompt_builder.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2024-02-04"
            
            with patch("src.llm.prompt_builder.SYSTEM_PROMPT_TEMPLATE") as mock_template:
                mock_template.format = MagicMock(return_value="System with date")
                
                result = prompt_builder.build_user_message_with_history(
                    "Query", sample_retrieval_results_dict, None
                )
                
                # Verify format was called with current_date
                mock_template.format.assert_called_once()
                call_kwargs = mock_template.format.call_args[1]
                assert "current_date" in call_kwargs
                assert call_kwargs["current_date"] == "2024-02-04"
    
    def test_build_user_message_with_history_calls_format_context(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that format_context is called for current query.
        
        Testing Concept: Verify method delegation
        """
        with patch.object(prompt_builder, 'format_context') as mock_format:
            mock_format.return_value = "Formatted"
            
            prompt_builder.build_user_message_with_history(
                "Query", sample_retrieval_results_dict, sample_conversation_history
            )
            
            mock_format.assert_called_once_with(sample_retrieval_results_dict)
    
    def test_build_user_message_with_history_with_long_history(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with very long conversation history.
        
        Testing Concept: Test large input
        """
        long_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(100)
        ]
        
        result = prompt_builder.build_user_message_with_history(
            "Query", sample_retrieval_results_dict, long_history
        )
        
        # Should have: system + 100 history + current = 102
        assert len(result) == 102


# ============================================================================
# TEST CLASS: Build Clarification Messages Tests
# ============================================================================


class TestBuildClarificationMessages:
    """Test build_clarification_messages functionality."""
    
    def test_build_clarification_messages_returns_list(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that method returns a list of messages.
        
        Testing Concept: Test return type
        """
        result = prompt_builder.build_clarification_messages(
            query="What visa?",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55
        )
        
        assert isinstance(result, list)
        assert len(result) == 2  # System + User
    
    def test_build_clarification_messages_has_system_message(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that first message is system message.
        
        Testing Concept: Test message structure
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55
        )
        
        assert result[0]["role"] == "system"
        assert "content" in result[0]
    
    def test_build_clarification_messages_has_user_message(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that second message is user message.
        
        Testing Concept: Test message structure
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55
        )
        
        assert result[1]["role"] == "user"
        assert "content" in result[1]
    
    def test_build_clarification_messages_includes_confidence_scores(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that confidence scores are included.
        
        Testing Concept: Test parameter usage
        """
        with patch("src.llm.prompt_builder.CLARIFICATION_USER_TEMPLATE") as mock_template:
            mock_template.format = MagicMock(return_value="Formatted")
            
            prompt_builder.build_clarification_messages(
                query="Query",
                context=sample_retrieval_results_dict,
                retrieval_confidence=0.6,
                llm_confidence=0.5,
                overall_confidence=0.55
            )
            
            # Verify all confidence scores were passed
            mock_template.format.assert_called_once()
            call_kwargs = mock_template.format.call_args[1]
            assert call_kwargs["retrieval_confidence"] == 0.6
            assert call_kwargs["llm_confidence"] == 0.5
            assert call_kwargs["overall_confidence"] == 0.55
    
    def test_build_clarification_messages_calls_format_context(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test that format_context is called.
        
        Testing Concept: Verify method delegation
        """
        with patch.object(prompt_builder, 'format_context') as mock_format:
            mock_format.return_value = "Formatted context"
            
            prompt_builder.build_clarification_messages(
                query="Query",
                context=sample_retrieval_results_dict,
                retrieval_confidence=0.6,
                llm_confidence=0.5,
                overall_confidence=0.55
            )
            
            mock_format.assert_called_once_with(sample_retrieval_results_dict)
    
    def test_build_clarification_messages_without_history(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test without conversation history.
        
        Testing Concept: Test None optional parameter
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55,
            conversation_history=None
        )
        
        assert len(result) == 2
        # User content should not have history prepended
        assert "Conversation History:" not in result[1]["content"]
    
    def test_build_clarification_messages_with_empty_history(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with empty conversation history.
        
        Testing Concept: Test empty list parameter
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55,
            conversation_history=[]
        )
        
        assert len(result) == 2
        # Empty history should not add history text
        assert "Conversation History:" not in result[1]["content"]
    
    def test_build_clarification_messages_with_history(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history, mock_logger
    ):
        """
        Test with conversation history.
        
        Testing Concept: Test history prepending
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55,
            conversation_history=sample_conversation_history
        )
        
        # User content should have history prepended
        assert "Conversation History:" in result[1]["content"]
        
        # Verify logging
        mock_logger.debug.assert_any_call(
            "history_text for clarification: %s",
            "user: What is a Schengen visa?\nassistant: A Schengen visa allows you to travel...\nuser: What documents do I need?"
        )
        mock_logger.debug.assert_any_call(
            "Prepending conversation history to clarification prompt..."
        )
    
    def test_build_clarification_messages_formats_history_correctly(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that history is formatted correctly.
        
        Testing Concept: Test string formatting
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55,
            conversation_history=sample_conversation_history
        )
        
        user_content = result[1]["content"]
        
        # Should contain formatted history
        assert "user: What is a Schengen visa?" in user_content
        assert "assistant: A Schengen visa allows you to travel..." in user_content
        assert "user: What documents do I need?" in user_content
    
    def test_build_clarification_messages_with_zero_confidence(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with zero confidence scores.
        
        Testing Concept: Test boundary values
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.0,
            llm_confidence=0.0,
            overall_confidence=0.0
        )
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_build_clarification_messages_with_high_confidence(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test with high confidence scores.
        
        Testing Concept: Test boundary values
        """
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.99,
            llm_confidence=0.98,
            overall_confidence=0.985
        )
        
        assert isinstance(result, list)
        assert len(result) == 2


# ============================================================================
# TEST CLASS: Build User Conversation Messages Tests
# ============================================================================


class TestBuildUserConversationMessages:
    """Test build_user_conversation_messages functionality."""
    
    def test_build_user_conversation_messages_returns_list(self, prompt_builder):
        """
        Test that method returns a list of messages.
        
        Testing Concept: Test return type
        """
        result = prompt_builder.build_user_conversation_messages("Test prompt")
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_build_user_conversation_messages_has_system_message(self, prompt_builder):
        """
        Test that first message is system message.
        
        Testing Concept: Test message structure
        """
        result = prompt_builder.build_user_conversation_messages("Test prompt")
        
        assert result[0]["role"] == "system"
        assert "content" in result[0]
        assert isinstance(result[0]["content"], str)
    
    def test_build_user_conversation_messages_has_user_message(self, prompt_builder):
        """
        Test that second message is user message.
        
        Testing Concept: Test message structure
        """
        user_prompt = "What is AI?"
        
        result = prompt_builder.build_user_conversation_messages(user_prompt)
        
        assert result[1]["role"] == "user"
        assert result[1]["content"] == user_prompt
    
    def test_build_user_conversation_messages_injects_current_date(self, prompt_builder):
        """
        Test that current date is injected into system prompt.
        
        Testing Concept: Test date injection
        """
        with patch("src.llm.prompt_builder.date") as mock_date:
            mock_date.today.return_value.isoformat.return_value = "2024-02-04"
            
            with patch("src.llm.prompt_builder.SYSTEM_PROMPT_TEMPLATE") as mock_template:
                mock_template.format = MagicMock(return_value="System with date")
                
                result = prompt_builder.build_user_conversation_messages("Prompt")
                
                # Verify format was called with current_date
                mock_template.format.assert_called_once()
                call_kwargs = mock_template.format.call_args[1]
                assert "current_date" in call_kwargs
                assert call_kwargs["current_date"] == "2024-02-04"
    
    def test_build_user_conversation_messages_includes_contact_fallback(
        self, prompt_builder
    ):
        """
        Test that contact fallback is included.
        
        Testing Concept: Test template parameter
        """
        with patch("src.llm.prompt_builder.SYSTEM_PROMPT_TEMPLATE") as mock_template:
            with patch("src.llm.prompt_builder.CONTACT_FALLBACK", "Contact support"):
                mock_template.format = MagicMock(return_value="System prompt")
                
                prompt_builder.build_user_conversation_messages("Prompt")
                
                # Verify contact_fallback was passed
                call_kwargs = mock_template.format.call_args[1]
                assert "contact_fallback" in call_kwargs
    
    def test_build_user_conversation_messages_with_empty_prompt(self, prompt_builder):
        """
        Test with empty prompt.
        
        Testing Concept: Test empty input
        """
        result = prompt_builder.build_user_conversation_messages("")
        
        assert len(result) == 2
        assert result[1]["content"] == ""
    
    def test_build_user_conversation_messages_with_long_prompt(self, prompt_builder):
        """
        Test with very long prompt.
        
        Testing Concept: Test large input
        """
        long_prompt = "Test " * 1000
        
        result = prompt_builder.build_user_conversation_messages(long_prompt)
        
        assert result[1]["content"] == long_prompt
    
    def test_build_user_conversation_messages_with_special_characters(
        self, prompt_builder
    ):
        """
        Test with special characters.
        
        Testing Concept: Test special character handling
        """
        prompt_with_special = "Test with émojis 🎉 and spëcial çhars\nNewline\tTab"
        
        result = prompt_builder.build_user_conversation_messages(prompt_with_special)
        
        assert result[1]["content"] == prompt_with_special
    
    def test_build_user_conversation_messages_with_unicode(self, prompt_builder):
        """
        Test with unicode characters.
        
        Testing Concept: Test unicode handling
        """
        unicode_prompt = "你好世界 こんにちは مرحبا"
        
        result = prompt_builder.build_user_conversation_messages(unicode_prompt)
        
        assert result[1]["content"] == unicode_prompt


# ============================================================================
# TEST CLASS: Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""
    
    def test_format_context_with_result_missing_content(self, prompt_builder):
        """
        Test handling when result is missing content field.
        
        Testing Concept: Test missing required field
        """
        result_missing_content = [
            {
                "metadata": {"document_name": "doc.pdf", "chunk_type": "text"},
                "relevance_score": 0.8
                # Missing content
            }
        ]
        
        result = prompt_builder.format_context(result_missing_content)
        
        # Should handle gracefully (content will be empty string)
        assert isinstance(result, str)
    
    def test_format_context_with_result_missing_relevance_score(self, prompt_builder):
        """
        Test handling when result is missing relevance_score.
        
        Testing Concept: Test missing field with default
        """
        result_missing_score = [
            {
                "content": "Content",
                "metadata": {"document_name": "doc.pdf", "chunk_type": "text"}
                # Missing relevance_score
            }
        ]
        
        result = prompt_builder.format_context(result_missing_score)
        
        # Should use 0.0 as default
        assert "0.00" in result
    
    def test_all_methods_work_together(
        self, prompt_builder, sample_retrieval_results_dict,
        sample_conversation_history
    ):
        """
        Test that all methods can be used together in sequence.
        
        Testing Concept: Integration test
        """
        # 1. Format context
        formatted = prompt_builder.format_context(sample_retrieval_results_dict)
        assert isinstance(formatted, str)
        
        # 2. Build user message
        user_msg = prompt_builder.build_user_message(
            "Query", sample_retrieval_results_dict
        )
        assert isinstance(user_msg, str)
        
        # 3. Build with history
        with_history = prompt_builder.build_user_message_with_history(
            "Query", sample_retrieval_results_dict, sample_conversation_history
        )
        assert isinstance(with_history, list)
        
        # 4. Build clarification
        clarification = prompt_builder.build_clarification_messages(
            "Query", sample_retrieval_results_dict, 0.6, 0.5, 0.55
        )
        assert isinstance(clarification, list)
        
        # 5. Build conversation messages
        conversation = prompt_builder.build_user_conversation_messages("Prompt")
        assert isinstance(conversation, list)
    
    def test_format_context_preserves_order(self, prompt_builder):
        """
        Test that context formatting preserves result order.
        
        Testing Concept: Test ordering preservation
        """
        ordered_results = [
            {
                "content": f"Content {i}",
                "metadata": {"document_name": f"doc{i}.pdf", "chunk_type": "text"},
                "relevance_score": 1.0 - (i * 0.1)
            }
            for i in range(5)
        ]
        
        result = prompt_builder.format_context(ordered_results)
        
        # Check that results appear in order
        pos0 = result.find("Content 0")
        pos1 = result.find("Content 1")
        pos2 = result.find("Content 2")
        
        assert pos0 < pos1 < pos2
    
    def test_conversation_history_handles_missing_role(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test history handling when role is missing.
        
        Testing Concept: Test missing dict key in history
        """
        history_missing_role = [
            {"content": "Message without role"}
        ]
        
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55,
            conversation_history=history_missing_role
        )
        
        # Should handle gracefully
        assert isinstance(result, list)
    
    def test_conversation_history_handles_missing_content(
        self, prompt_builder, sample_retrieval_results_dict
    ):
        """
        Test history handling when content is missing.
        
        Testing Concept: Test missing dict key in history
        """
        history_missing_content = [
            {"role": "user"}
        ]
        
        result = prompt_builder.build_clarification_messages(
            query="Query",
            context=sample_retrieval_results_dict,
            retrieval_confidence=0.6,
            llm_confidence=0.5,
            overall_confidence=0.55,
            conversation_history=history_missing_content
        )
        
        # Should handle gracefully
        assert isinstance(result, list)


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("num_results", [0, 1, 2, 5, 10, 100])
    def test_format_context_with_various_result_counts(
        self, prompt_builder, num_results
    ):
        """
        Test formatting with various numbers of results.
        
        Testing Concept: Parameterized count testing
        """
        results = [
            {
                "content": f"Content {i}",
                "metadata": {"document_name": f"doc{i}.pdf", "chunk_type": "text"},
                "relevance_score": 0.9
            }
            for i in range(num_results)
        ]
        
        result = prompt_builder.format_context(results)
        
        if num_results == 0:
            assert result == "NO_CONTEXT"
        else:
            assert isinstance(result, str)
            assert len(result) > 0
    
    @pytest.mark.parametrize("chunk_type", ["text", "heading", "table", "list", "code"])
    def test_format_context_with_various_chunk_types(
        self, prompt_builder, chunk_type
    ):
        """
        Test formatting with various chunk types.
        
        Testing Concept: Parameterized type testing
        """
        results = [
            {
                "content": "Test content",
                "metadata": {"document_name": "doc.pdf", "chunk_type": chunk_type},
                "relevance_score": 0.8
            }
        ]
        
        result = prompt_builder.format_context(results)
        
        assert f"Type: {chunk_type}" in result
    
    @pytest.mark.parametrize("score", [0.0, 0.1, 0.5, 0.9, 0.99, 1.0])
    def test_format_context_with_various_scores(self, prompt_builder, score):
        """
        Test formatting with various relevance scores.
        
        Testing Concept: Parameterized score testing
        """
        results = [
            {
                "content": "Content",
                "metadata": {"document_name": "doc.pdf", "chunk_type": "text"},
                "relevance_score": score
            }
        ]
        
        result = prompt_builder.format_context(results)
        
        # Check score is formatted to 2 decimals
        formatted_score = f"{score:.2f}"
        assert formatted_score in result


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.llm.prompt_builder",
        "--cov-report=term-missing"
    ])


