"""Test that conversation history is fetched from DB only once per session."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.chat.conversation_repository import CompositeConversationRepository
from src.models import Message
from datetime import datetime, timezone


def test_db_queried_only_when_file_empty():
    """Test that DB is only queried when file storage is empty (first message)."""
    
    repo = CompositeConversationRepository()
    user_id = 999
    
    # Mock file repository to return empty (simulating first message)
    with patch.object(repo.file_repository, 'get_messages', return_value=[]):
        # Mock DB repository to return some messages
        db_messages = [
            Message(
                content="Previous summary",
                role="assistant",
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                metadata={"is_summary": True}
            )
        ]
        with patch.object(repo.db_repository, 'get_messages', return_value=db_messages) as mock_db_get:
            # First call - file is empty, should query DB
            messages = repo.get_messages(user_id)
            
            # DB should have been queried
            mock_db_get.assert_called_once_with(user_id)
            assert len(messages) == 1
            assert messages[0].content == "Previous summary"


def test_db_not_queried_when_file_has_messages():
    """Test that DB is NOT queried when file storage has messages (ongoing conversation)."""
    
    repo = CompositeConversationRepository()
    user_id = 999
    
    # Mock file repository to return messages (simulating ongoing conversation)
    file_messages = [
        Message(
            content="User message 1",
            role="user",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            metadata={}
        ),
        Message(
            content="Assistant response 1",
            role="assistant",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            metadata={}
        )
    ]
    
    with patch.object(repo.file_repository, 'get_messages', return_value=file_messages):
        # Mock DB repository - should NOT be called
        with patch.object(repo.db_repository, 'get_messages') as mock_db_get:
            # Call get_messages - file has messages, should NOT query DB
            messages = repo.get_messages(user_id)
            
            # DB should NOT have been queried
            mock_db_get.assert_not_called()
            assert len(messages) == 2
            assert messages[0].content == "User message 1"
            assert messages[1].content == "Assistant response 1"


def test_multiple_get_messages_only_queries_db_once():
    """Test that multiple get_messages calls don't repeatedly query DB."""
    
    repo = CompositeConversationRepository()
    user_id = 999
    
    # First call - file empty, should query DB
    with patch.object(repo.file_repository, 'get_messages', return_value=[]):
        with patch.object(repo.db_repository, 'get_messages', return_value=[]) as mock_db_get:
            repo.get_messages(user_id)
            assert mock_db_get.call_count == 1
    
    # Subsequent calls - file has messages, should NOT query DB
    file_messages = [
        Message(
            content="Message",
            role="user",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            metadata={}
        )
    ]
    
    with patch.object(repo.file_repository, 'get_messages', return_value=file_messages):
        with patch.object(repo.db_repository, 'get_messages') as mock_db_get:
            # Call multiple times
            repo.get_messages(user_id)
            repo.get_messages(user_id)
            repo.get_messages(user_id)
            
            # DB should NOT be called for any of these
            mock_db_get.assert_not_called()
