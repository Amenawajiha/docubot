from datetime import datetime, timedelta, timezone

from src.chat.conversation_manager import ConversationManager
from src.models import Message


def test_format_with_summary_returns_recent_messages():
    """Test that _format_with_summary returns recent messages correctly.
    
    Note: Clarification context is now preserved by passing conversation history
    to the clarification generation process, not by special handling in
    _format_with_summary.
    """
    manager = ConversationManager()

    base = datetime.now(timezone.utc)

    # Old messages (would be summarized)
    old_user = Message(content="old question", role="user", timestamp=base - timedelta(minutes=10), user_id=1, metadata={})
    old_assistant = Message(content="old answer", role="assistant", timestamp=base - timedelta(minutes=9), user_id=1, metadata={})

    # Recent messages
    recent_user = Message(content="recent question", role="user", timestamp=base - timedelta(minutes=1), user_id=1, metadata={})
    recent_assistant = Message(content="recent answer", role="assistant", timestamp=base, user_id=1, metadata={})

    messages = [old_user, old_assistant, recent_user, recent_assistant]

    # Use recent_count=2 so old messages would be summarized
    formatted = manager._format_with_summary(messages, recent_count=2)

    # formatted[0] is the system summary, the rest are chat messages
    chat_messages = formatted[1:]

    # Ensure recent messages appear in the returned chat messages
    contents = [m["content"] for m in chat_messages]
    assert "recent question" in contents, "Recent user message was not preserved"
    assert "recent answer" in contents, "Recent assistant message was not preserved"
    # Old messages should be summarized, not present verbatim
    assert "old question" not in contents, "Old message should be summarized, not preserved verbatim"
