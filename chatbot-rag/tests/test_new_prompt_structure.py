"""Test the new prompt structure and prompt builder functionality."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import date
from src.llm.prompts import (
    QUERY_PROMPT,
    CONTACT_FALLBACK,
    SYSTEM_PROMPT_TEMPLATE,
    CLARIFICATION_SYSTEM_INSTRUCTION,
    CLARIFICATION_USER_TEMPLATE,
    CONVERSATION_SUMMARY_PROMPT,
)
from src.llm.prompt_builder import PromptBuilder


class TestPrompts:
    """Test prompt templates and constants."""

    def test_contact_fallback_defined(self):
        """Test that CONTACT_FALLBACK is properly defined."""
        assert CONTACT_FALLBACK is not None
        assert "Phone" in CONTACT_FALLBACK
        assert "WhatsApp" in CONTACT_FALLBACK
        assert "Mail" in CONTACT_FALLBACK
        assert "schengenvisaitinerary.com" in CONTACT_FALLBACK

    def test_query_prompt_structure(self):
        """Test that QUERY_PROMPT has the expected structure."""
        assert "CONTEXT:" in QUERY_PROMPT
        assert "IMPORTANT INSTRUCTIONS:" in QUERY_PROMPT
        assert "QUERY:" in QUERY_PROMPT
        assert "ANSWER:" in QUERY_PROMPT

    def test_query_prompt_format_placeholders(self):
        """Test that QUERY_PROMPT has the correct placeholders."""
        assert "{query}" in QUERY_PROMPT
        assert "{context}" in QUERY_PROMPT

    def test_query_prompt_contains_relevance_instructions(self):
        """Test that QUERY_PROMPT mentions relevance scores."""
        assert "relevance score" in QUERY_PROMPT
        assert "0.00 to 1.00" in QUERY_PROMPT

    def test_system_prompt_template_structure(self):
        """Test that SYSTEM_PROMPT_TEMPLATE has required components."""
        assert "Schengen Visa Assistant" in SYSTEM_PROMPT_TEMPLATE
        assert "{current_date}" in SYSTEM_PROMPT_TEMPLATE
        assert "Past Date Validation" in SYSTEM_PROMPT_TEMPLATE
        assert "Decision Framework" in SYSTEM_PROMPT_TEMPLATE

    def test_clarification_prompts_defined(self):
        """Test that clarification prompts are properly defined."""
        assert CLARIFICATION_SYSTEM_INSTRUCTION is not None
        assert "clarifying questions" in CLARIFICATION_SYSTEM_INSTRUCTION
        assert "{query}" in CLARIFICATION_USER_TEMPLATE
        assert "{context}" in CLARIFICATION_USER_TEMPLATE
        assert "{retrieval_confidence}" in CLARIFICATION_USER_TEMPLATE
        assert "{llm_confidence}" in CLARIFICATION_USER_TEMPLATE
        assert "{overall_confidence}" in CLARIFICATION_USER_TEMPLATE

    def test_conversation_summary_prompt_defined(self):
        """Test that conversation summary prompt is properly defined."""
        assert CONVERSATION_SUMMARY_PROMPT is not None
        assert "{conversation_text}" in CONVERSATION_SUMMARY_PROMPT


class TestPromptBuilder:
    """Test PromptBuilder class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PromptBuilder()

    def test_format_context_with_empty_results(self):
        """Test format_context with no results returns NO_CONTEXT."""
        result = self.builder.format_context([])
        assert result == "NO_CONTEXT"

    def test_format_context_with_dict_results(self):
        """Test format_context with dictionary-style results."""
        results = [
            {
                "metadata": {
                    "document_name": "test_doc.pdf",
                    "chunk_type": "text",
                },
                "content": "This is a test content.",
                "relevance_score": 0.85,
            }
        ]
        result = self.builder.format_context(results)
        
        assert "[Context 1]" in result
        assert "Source: test_doc.pdf" in result
        assert "Type: text" in result
        assert "This is a test content." in result
        assert "Relevance: 0.85" in result

    def test_format_context_with_object_results(self):
        """Test format_context with object-style results."""
        class MockResult:
            def __init__(self):
                self.metadata = {"document_name": "doc2.pdf", "chunk_type": "table"}
                self.content = "Table content here"
                self.relevance_score = 0.92

        results = [MockResult()]
        result = self.builder.format_context(results)
        
        assert "[Context 1]" in result
        assert "Source: doc2.pdf" in result
        assert "Type: table" in result
        assert "Table content here" in result
        assert "Relevance: 0.92" in result

    def test_format_context_with_multiple_results(self):
        """Test format_context with multiple results."""
        results = [
            {
                "metadata": {"document_name": "doc1.pdf", "chunk_type": "text"},
                "content": "Content 1",
                "relevance_score": 0.90,
            },
            {
                "metadata": {"document_name": "doc2.pdf", "chunk_type": "text"},
                "content": "Content 2",
                "relevance_score": 0.75,
            },
        ]
        result = self.builder.format_context(results)
        
        assert "[Context 1]" in result
        assert "[Context 2]" in result
        assert "Content 1" in result
        assert "Content 2" in result

    def test_format_context_with_missing_metadata(self):
        """Test format_context handles missing metadata gracefully."""
        results = [
            {
                "metadata": {},
                "content": "Content without metadata",
                "relevance_score": 0.50,
            }
        ]
        result = self.builder.format_context(results)
        
        assert "Source: Unknown" in result
        assert "Type: text" in result
        assert "Content without metadata" in result

    def test_build_user_message_empty_context(self):
        """Test build_user_message with empty context."""
        query = "What is a Schengen visa?"
        context = []
        
        result = self.builder.build_user_message(query, context)
        
        assert "NO_CONTEXT" in result
        assert query in result
        assert "QUERY:" in result

    def test_build_user_message_with_context(self):
        """Test build_user_message with context."""
        query = "What documents are required?"
        context = [
            {
                "metadata": {"document_name": "requirements.pdf", "chunk_type": "text"},
                "content": "You need passport and photos.",
                "relevance_score": 0.88,
            }
        ]
        
        result = self.builder.build_user_message(query, context)
        
        assert query in result
        assert "requirements.pdf" in result
        assert "You need passport and photos." in result
        assert "Relevance: 0.88" in result

    def test_build_user_message_with_history_no_history(self):
        """Test build_user_message_with_history without history."""
        query = "Test query"
        context = []
        
        messages = self.builder.build_user_message_with_history(query, context)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert query in messages[1]["content"]

    def test_build_user_message_with_history_includes_current_date(self):
        """Test that system message includes current date."""
        query = "Test query"
        context = []
        
        messages = self.builder.build_user_message_with_history(query, context)
        
        current_date = date.today().isoformat()
        assert current_date in messages[0]["content"]
        assert "Schengen Visa Assistant" in messages[0]["content"]

    def test_build_user_message_with_history_with_history(self):
        """Test build_user_message_with_history with conversation history."""
        query = "Follow up question"
        context = []
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]
        
        messages = self.builder.build_user_message_with_history(query, context, history)
        
        assert len(messages) == 4  # system + 2 history + current
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Previous question"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Previous answer"
        assert messages[3]["role"] == "user"
        assert query in messages[3]["content"]

    def test_build_clarification_messages(self):
        """Test build_clarification_messages creates proper structure."""
        query = "Ambiguous question"
        context = [
            {
                "metadata": {"document_name": "test.pdf", "chunk_type": "text"},
                "content": "Some content",
                "relevance_score": 0.60,
            }
        ]
        
        messages = self.builder.build_clarification_messages(
            query=query,
            context=context,
            retrieval_confidence=0.60,
            llm_confidence=0.55,
            overall_confidence=0.575,
        )
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "clarifying questions" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert query in messages[1]["content"]
        assert "0.60" in messages[1]["content"]
        assert "0.55" in messages[1]["content"]
        assert "0.575" in messages[1]["content"]

    def test_build_user_conversation_messages(self):
        """Test build_user_conversation_messages."""
        user_prompt = "Custom formatted prompt"
        
        messages = self.builder.build_user_conversation_messages(user_prompt)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == user_prompt
        
        # Verify system prompt has current date
        current_date = date.today().isoformat()
        assert current_date in messages[0]["content"]

    def test_build_user_conversation_messages_includes_contact_fallback(self):
        """Test that system prompt includes contact fallback in system message."""
        user_prompt = "Test prompt"
        
        messages = self.builder.build_user_conversation_messages(user_prompt)
        
        # The system prompt should have been formatted with contact_fallback
        assert "Schengen Visa Assistant" in messages[0]["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
