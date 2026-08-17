"""Conversation repository for storing and retrieving conversation history."""

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List

from src.chat.schemas import ConversationORM
from src.models import Message
from src.utils.config_loader import get_config
from src.utils.db_enter_exit_mixin import DBEnterExitMixin
from src.utils.log_helper import logger


class IConversationRepository(ABC):
    """Abstract base class for conversation storage."""

    def __init__(self):
        self._recent_count = get_config("conversation.recent_count")

    @abstractmethod
    def save_message(self, user_id: int, message: Message) -> None:
        """Save a message to storage."""

    @abstractmethod
    def get_messages(self, user_id: int) -> List[Message]:
        """Retrieve messages for a user."""

    @abstractmethod
    def delete_conversation(self, user_id: int) -> None:
        """Delete all messages for a user."""


class DatabaseConversationRepository(IConversationRepository, DBEnterExitMixin):
    """Repository that stores conversations in PostgreSQL database using SQLAlchemy."""

    def __init__(self):
        """Initialize database conversation repository."""
        super().__init__()
        self._db_helper = None
        self._db_session = None
        self.messages = []

    def save_message(self, user_id: int, message: Message) -> None:
        """
        Save a message to the database.

        Args:
            user_id: User identifier
            message: Message to save
        """
        # Only persist summary messages to DB to avoid per-message records
        if not message.metadata or not message.metadata.get("is_summary"):
            # Skip storing regular messages in DB; file storage keeps them
            return

        record = ConversationORM(
            user_id=user_id,
            content=message.content,
            timestamp=message.timestamp,
            meta_data=message.metadata,
        )
        with self:
            try:
                # Insert summary record; multiple sessions per user are allowed
                self._db_session.add(record)
                self._db_session.commit()
            except Exception as e:
                logger.error("Error saving summary to DB: %s", e)
                raise e

    def save_summary(self, user_id: int, summary_message: Message) -> None:
        """
        Insert a single summary record for a user's session.

        We intentionally do NOT upsert by session id — each WebSocket session
        that disconnects will produce one summary record (timestamp differentiates sessions).
        """
        with self:
            try:
                record = ConversationORM(
                    user_id=user_id,
                    content=summary_message.content,
                    timestamp=summary_message.timestamp,
                    meta_data=summary_message.metadata,
                )
                self._db_session.add(record)
                self._db_session.commit()
            except Exception as e:
                logger.error("Error saving session summary to DB: %s", e)
                raise e

    def get_messages(self, user_id: int) -> List[Message]:
        """
        Retrieve messages for a user from the database.

        Args:
            user_id: User identifier

        Returns:
            List of messages, ordered by timestamp (most recent last)
        """
        try:
            with self:
                # Query the last N messages
                # Note: We need to sort by timestamp DESC to get recent ones, then reverse
                records = (
                    self._db_session.query(ConversationORM)
                    .filter(ConversationORM.user_id == user_id)
                    .order_by(ConversationORM.timestamp.desc())
                    .limit(self._recent_count)
                    .all()
                )

                messages = []
                for record in reversed(records):
                    # DB stores summaries only; set role to 'assistant' by default
                    messages.append(
                        Message(
                            content=record.content,
                            role=(
                                record.meta_data.get("role")
                                if record.meta_data and record.meta_data.get("role")
                                else "assistant"
                            ),
                            timestamp=record.timestamp,
                            user_id=record.user_id,
                            metadata=record.meta_data or {},
                        )
                    )
                return messages
        except Exception as e:
            logger.error("Error retrieving messages from DB: %s", e)
            return []

    def delete_conversation(self, user_id: int) -> None:
        """
        Delete all messages for a user from the database.

        Args:
            user_id: User identifier
        """
        with self:
            try:
                self._db_session.query(ConversationORM).filter(
                    ConversationORM.user_id == user_id
                ).delete()
                self._db_session.commit()
            except Exception as e:
                logger.error("Error deleting conversation from DB: %s", e)
                raise e


class FileConversationRepository(IConversationRepository):
    """Repository that stores conversations as JSON files."""

    def __init__(self):
        """
        Initialize file conversation repository.

        Args:
            storage_path: Directory path to store conversation files
        """
        super().__init__()
        self.storage_path = get_config("conversation.storage_path")
        os.makedirs(self.storage_path, exist_ok=True)

    def _get_file_path(self, user_id: int) -> str:
        """Get the file path for a user's conversation."""
        return os.path.join(self.storage_path, f"{user_id}.json")

    def save_message(self, user_id: int, message: Message) -> None:
        """
        Save a message to a JSON file.

        Args:
            user_id: User identifier
            message: Message to save
        """
        file_path = self._get_file_path(user_id)

        # Prepare new message data
        message_data = {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "user_id": user_id,
            "metadata": message.metadata,
        }

        if os.path.exists(file_path):
            with open(file_path, "r+", encoding="utf-8") as f:
                messages = json.load(f)
                messages.append(message_data)
                f.seek(0)
                json.dump(messages, f, indent=2, ensure_ascii=False)
                f.truncate()
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([message_data], f, indent=2, ensure_ascii=False)

    def get_messages(self, user_id: int) -> List[Message]:
        """
        Retrieve messages for a user from JSON file.

        Args:
            user_id: User identifier

        Returns:
            List of messages, ordered by timestamp (most recent last)
        """
        file_path = self._get_file_path(user_id)

        if not os.path.exists(file_path):
            return []

        # Load messages from file
        with open(file_path, "r", encoding="utf-8") as f:
            messages_data = json.load(f)

        # Convert to Message objects (get last N messages)
        messages = []
        for msg_data in messages_data[-self._recent_count :]:
            # Parse ISO timestamp and ensure timezone-aware (assume UTC if absent)
            dt = datetime.fromisoformat(msg_data["timestamp"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            messages.append(
                Message(
                    content=msg_data["content"],
                    role=msg_data["role"],
                    timestamp=dt,
                    user_id=user_id,
                    metadata=msg_data.get("metadata", {}),
                )
            )

        return messages

    def delete_conversation(self, user_id: int) -> None:
        """
        Delete conversation file for a user.

        Args:
            user_id: User identifier
        """
        file_path = self._get_file_path(user_id)
        if os.path.exists(file_path):
            os.remove(file_path)

    def cleanup_old_conversations(self, days: int = 7) -> int:
        """
        Delete conversation files older than specified days.

        Args:
            days: Delete files older than this many days

        Returns:
            Number of files deleted
        """

        if not os.path.exists(self.storage_path):
            return 0

        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0

        for filename in os.listdir(self.storage_path):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(self.storage_path, filename)

            # Check file modification time
            if os.path.getmtime(file_path) < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception:
                    pass  # Skip files we can't delete

        return deleted_count


class CompositeConversationRepository(IConversationRepository):
    """Repository that combines database and file storage for conversations."""

    def __init__(self):
        """Initialize composite conversation repository."""
        super().__init__()
        self.db_repository = DatabaseConversationRepository()
        self.file_repository = FileConversationRepository()

    def save_message(self, user_id: int, message: Message) -> None:
        """
        Save a message to both database and file storage.

        Args:
            user_id: User identifier
            message: Message to save
        """
        self.file_repository.save_message(user_id, message)
        self.db_repository.save_message(user_id, message)

    def get_messages(self, user_id: int) -> List[Message]:
        """
        Retrieve messages for a user from file storage.

        Args:
            user_id: User identifier

        Returns:
            List of messages, ordered by timestamp (most recent last)
        """
        last_n_messages = self.file_repository.get_messages(user_id)

        # Only query the DB if file storage has no messages for the user. This
        # reduces DB load for active sessions persisted in file storage.
        if last_n_messages:
            db_summary_messages = []
        else:
            db_summary_messages = self.db_repository.get_messages(user_id)

        # Combine messages from both repositories and normalize timestamps
        combined_messages = last_n_messages + db_summary_messages

        # Ensure all timestamps are timezone-aware (assume UTC for naive)
        for msg in combined_messages:
            if msg.timestamp and msg.timestamp.tzinfo is None:
                msg.timestamp = msg.timestamp.replace(tzinfo=timezone.utc)

        combined_messages.sort(key=lambda msg: msg.timestamp)
        return combined_messages

    def delete_conversation(self, user_id: int) -> None:
        """
        Delete all messages for a user from both database and file storage.

        Args:
            user_id: User identifier
        """
        self.file_repository.delete_conversation(user_id)
        self.db_repository.delete_conversation(user_id)
