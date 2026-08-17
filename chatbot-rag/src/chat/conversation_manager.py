"""Conversation manager for handling conversation history and context."""

from typing import Dict, List, Optional

from src.chat.conversation_repository import (
    FileConversationRepository,
    IConversationRepository,
)
from src.chat.conversation_summarizer import ConversationSummarizer
from src.models import Message
from src.utils.config_loader import get_config


class ConversationManager:
    """Manages conversation history with optional summarization."""

    def __init__(self, repository: IConversationRepository = None, llm=None):
        self.repository = repository or FileConversationRepository()
        self.summarizer = ConversationSummarizer(llm=llm)
        self.enable_summarization = get_config("conversation.enable_summarization")

    def add_message(
        self,
        message: Message,
        user_id: int,
    ) -> None:
        """
        Add a message to the conversation history.

        Args:
            user_id: User identifier
            message: Message to add
        """
        # Only save messages for logged-in users
        if not user_id:
            return

        self.repository.save_message(user_id, message)

        if self.enable_summarization:
            messages = self.repository.get_messages(user_id)

            if len(messages) > get_config("conversation.storage_threshold"):
                old_messages = messages[:-5]
                summary_message = self.summarizer.summarize_for_storage(old_messages)

                # Delete old messages and save summary
                # Note: This requires additional repository method
                # For now, we'll just save the summary
                self.repository.save_message(user_id, summary_message)

    def get_messages_for_llm(self, user_id: int) -> List[Dict[str, str]]:
        """
        Get conversation messages formatted for LLM chat API.

        Returns messages in OpenAI chat format with optional summarization.

        Args:
            user_id: User identifier

        Returns:
            List of message dicts: [{"role": "user", "content": "..."}, ...]
        """
        messages = self.repository.get_messages(user_id=user_id)

        if not messages:
            return []

        if self.enable_summarization:
            if len(messages) > get_config("conversation.retrieval_threshold"):
                return self._format_with_summary(messages)

        return self._format_as_chat_messages(messages)

    def clear_conversation(self, user_id: int) -> None:
        """
        Clear all conversation history for a user.

        Args:
            user_id: User identifier
        """
        self.repository.delete_conversation(user_id)

    def generate_summary_message(self, user_id: int) -> Optional[Message]:
        """
        Generate a single summary message for a user's entire conversation.

        Args:
            user_id: User identifier

        Returns:
            Summary message or None if no messages exist.
        """
        messages = self.repository.get_messages(user_id)
        if not messages:
            return None

        summary_message = self.summarizer.summarize_for_storage(messages)
        summary_message.user_id = user_id
        return summary_message

    def _format_as_chat_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        Format messages as chat API format.

        Args:
            messages: List of Message objects

        Returns:
            List of message dicts for chat API
        """
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Enforce pairing: The sequence MUST start with a 'user' message. 
        # If it starts with 'assistant', drop the orphaned assistant message.
        while formatted_messages and formatted_messages[0]["role"] != "user":
            formatted_messages.pop(0)
            
        return formatted_messages

    def _format_with_summary(
        self, messages: List[Message], recent_count: int = 5
    ) -> List[Dict[str, str]]:
        """
        Format messages with summarization for chat API.

        Args:
            messages: All messages
            recent_count: Number of recent messages to keep in full

        Returns:
            List of message dicts with summary + recent messages
        """
        if len(messages) <= recent_count:
            return self._format_as_chat_messages(messages)

        # Split into old and recent
        old_messages = messages[:-recent_count]
        recent_messages = messages[-recent_count:]

        # Get summary of old messages
        summary_text = self.summarizer.summarize_for_retrieval(old_messages)

        # Build result: summary as system message + recent messages
        result = [
            {
                "role": "system",
                "content": f"Previous conversation summary: {summary_text}",
            }
        ]
        formatted_recent = [{"role": msg.role, "content": msg.content} for msg in recent_messages]
        result.extend(formatted_recent)

        return result

    def format_history_for_chat(
        self, messages: List[Message]
    ) -> tuple[List[Dict[str, str]], bool, int, Optional[str]]:
        """
        Format messages for chat LLM context, summarizing older messages if len(messages) > retrieval_threshold.
        Returns: (formatted_messages, was_summarized, summarized_count, summary_text)
        """
        threshold = get_config("conversation.retrieval_threshold", default=20)
        recent_count = get_config("conversation.recent_count", default=10)

        if not self.enable_summarization or len(messages) <= threshold or len(messages) <= recent_count:
            return (self._format_as_chat_messages(messages), False, 0, None)

        old_messages = messages[:-recent_count]
        recent_messages = messages[-recent_count:]

        if hasattr(self.summarizer, "summarize_messages"):
            summary_text = self.summarizer.summarize_messages(old_messages)
        else:
            summary_text = self.summarizer.summarize_for_retrieval(old_messages)

        result = [
            {
                "role": "system",
                "content": f"Previous conversation summary: {summary_text}",
            }
        ]
        result.extend(self._format_as_chat_messages(recent_messages))

        return (result, True, len(old_messages), summary_text)

    def cleanup_old_conversations(self, days: int = 7) -> int:
        """
        Delete old conversation files.

        Args:
            days: Delete conversations older than this many days

        Returns:
            Number of conversations deleted
        """
        if hasattr(self.repository, "cleanup_old_conversations"):
            return self.repository.cleanup_old_conversations(days)
        return 0
