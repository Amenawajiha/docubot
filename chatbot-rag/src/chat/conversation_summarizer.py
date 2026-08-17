"""Conversation summarizer for compressing conversation history."""

from datetime import datetime, timezone
from typing import List

from src.utils.config_loader import get_config

from src.llm.llm_orchestrator import LLMOrchestrator
from src.llm.prompts import CONVERSATION_SUMMARY_PROMPT
from src.models import Message


class ConversationSummarizer:
    """Manages conversation summarization for storage and retrieval."""

    def __init__(self, llm=None):
        """
        Initialize conversation summarizer.
        """
        self.llm_orchestrator = llm or LLMOrchestrator()
        self.__recent_count = get_config("conversation.recent_count")

    def summarize_messages(self, messages: List[Message]) -> str:
        """
        Summarize a given list of messages into a concise string summary.
        """
        conversation_text = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in messages]
        )
        summary_prompt = CONVERSATION_SUMMARY_PROMPT.format(
            conversation_text=conversation_text
        )
        summary, _ = self.llm_orchestrator.send_message(summary_prompt)
        return summary.strip()

    def summarize_for_storage(self, messages: List[Message]) -> Message:
        """
        Compress old conversations to save DB space.

        Purpose: Create a single summary message to replace old messages
        When: Triggered when message count > 50
        How: Summarize messages 1-45, keep last 5 as-is

        Args:
            messages: List of messages to summarize (typically messages[:-5])

        Returns:
            Single summary Message that replaces old messages in DB
        """
        # Build conversation text from messages
        conversation_text = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in messages]
        )

        summary_prompt = CONVERSATION_SUMMARY_PROMPT.format(
            conversation_text=conversation_text
        )

        # Generate summary using LLM
        summary_content, _ = self.llm_orchestrator.send_message(summary_prompt)

        # Create summary message
        summary_message = Message(
            content=f"[Summary of previous conversation]: {summary_content.strip()}",
            role="assistant",
            timestamp=datetime.now(timezone.utc),
            user_id=messages[0].user_id if messages else 0,  # Using 0 as system user ID
            metadata={"is_summary": True, "summarized_count": len(messages)},
        )

        return summary_message

    def summarize_for_retrieval(self, messages: List[Message]) -> str:
        """
        Reduce tokens when sending context to LLM.

        Purpose: Summarize older messages, keep recent messages in full detail
        When: Called by get_messages_for_llm() when > 20 messages
        How: Summarize older messages, keep recent 5 in full

        Args:
            messages: All messages in conversation
            recent_count: Number of recent messages to keep in full (default: 5)

        Returns:
            String formatted for LLM prompt with summary + recent messages
        """
        if len(messages) <= self.__recent_count:
            # Not enough messages to summarize, return all
            return self._format_messages(messages)

        # Split into old (to summarize) and recent (keep as-is)
        old_messages = messages[: -self.__recent_count]
        recent_messages = messages[-self.__recent_count :]

        # Build conversation text from old messages
        old_conversation_text = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in old_messages]
        )

        summary_prompt = CONVERSATION_SUMMARY_PROMPT.format(
            conversation_text=old_conversation_text
        )

        summary, _ = self.llm_orchestrator.send_message(summary_prompt)

        # Format output: summary + recent messages
        context = f"Previous conversation summary: {summary.strip()}\n\n"
        context += "Recent conversation:\n"
        context += self._format_messages(recent_messages)

        return context

    def _format_messages(self, messages: List[Message]) -> str:
        """
        Format messages as conversation text.

        Args:
            messages: List of messages to format

        Returns:
            Formatted conversation string
        """
        return "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
