import json
from pathlib import Path

import pytest

from src.llm.prompt_builder import PromptBuilder


@pytest.mark.asyncio
async def test_clarification_prompt_includes_conversation_history():
    """PromptBuilder should include the prior conversation when building clarification messages."""
    conv_path = Path('conversations') / '11.json'
    assert conv_path.exists(), "Expected conversations/11.json to exist for this test"

    data = json.loads(conv_path.read_text(encoding='utf-8'))
    conversation_history = [{'role': m['role'], 'content': m['content']} for m in data]

    builder = PromptBuilder()
    messages = builder.build_clarification_messages(
        query='Which office do you mean?',
        context=[],
        retrieval_confidence=0.2,
        llm_confidence=0.3,
        overall_confidence=0.25,
        conversation_history=conversation_history,
    )

    # Expect two messages: system + user prompt; user prompt should include the conversation history
    assert len(messages) == 2
    user_content = messages[1]['content']
    assert 'Conversation History:' in user_content
    # Ensure at least one snippet from the stored conversation appears in the prompt
    assert any(entry['content'] in user_content for entry in conversation_history)
