"""Test that clarification messages are properly included in conversation context."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Message
from src.response_manager import ResponseManager


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_services():
    """Mock all service dependencies."""
    with patch("src.response_manager.get_service_manager") as mock_sm:
        # Create mock service manager
        service_manager = MagicMock()
        mock_sm.return_value = service_manager

        # Mock vector retriever
        vector_retriever = MagicMock()
        vector_retriever.retrieve_with_reranking.return_value = [
            MagicMock(
                content="TLScontact phone for NYC: +1-555-0100",
                metadata={"source": "contact.pdf"},
                relevance_score=0.3,  # Low relevance
            )
        ]
        service_manager.get_vector_retriever.return_value = vector_retriever

        # Mock LLM orchestrator
        llm_orchestrator = MagicMock()
        llm_orchestrator.send_messages.return_value = (
            "I don't know the answer.",
            [{"token": "I", "logprob": -0.5}],
        )
        service_manager.get_llm_orchestrator.return_value = llm_orchestrator

        # Mock confidence scorer
        confidence_scorer = MagicMock()
        from src.models import ConfidenceResult

        confidence_scorer.run.return_value = ConfidenceResult(
            retrieval_confidence=0.3,
            llm_confidence=0.4,
            overall_confidence=0.35,
            is_confident=False,
            confidence_breakdown={"retrieval": 0.3, "llm": 0.4},
        )
        service_manager.get_confidence_scorer.return_value = confidence_scorer

        # Mock prompt builder - use actual implementation to test history passing
        from src.llm.prompt_builder import PromptBuilder

        prompt_builder = PromptBuilder()
        service_manager.get_prompt_builder.return_value = prompt_builder

        # Mock clarification manager
        clarification_manager = MagicMock()
        clarification_manager.should_clarify.return_value = True
        clarification_manager.generate_clarifying_question.return_value = (
            "Which city do you mean?"
        )
        service_manager.get_clarification_manager.return_value = clarification_manager

        yield {
            "service_manager": service_manager,
            "vector_retriever": vector_retriever,
            "llm_orchestrator": llm_orchestrator,
            "confidence_scorer": confidence_scorer,
            "prompt_builder": prompt_builder,
            "clarification_manager": clarification_manager,
        }


@pytest.mark.asyncio
async def test_clarification_included_in_history(mock_websocket, mock_services):
    """Test that clarification messages are included in subsequent conversation history."""

    # Create response manager
    with patch("src.response_manager.get_config", return_value=0.0):
        manager = ResponseManager(mock_websocket, is_authenticated=False)

    user_id = 11

    # First query - should trigger clarification
    await manager.handle_query("what the phone number of tlscontact?", user_id)

    # Verify clarification was sent
    assert mock_websocket.send_json.call_count == 1
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "clarification"
    assert "Which city" in call_args["content"]

    # Get conversation history after first clarification
    history_after_first = manager.conversation_manager.get_messages_for_llm(user_id)
    print("\n=== History after first clarification ===")
    for msg in history_after_first:
        print(f"  {msg['role']}: {msg['content'][:100]}...")

    # Verify history contains user query and clarification
    assert len(history_after_first) >= 2
    assert history_after_first[-2]["role"] == "user"
    assert history_after_first[-1]["role"] == "assistant"
    assert "clarification" in str(
        history_after_first[-1]
    ).lower() or "which" in history_after_first[-1]["content"].lower()

    # Reset mocks for second query
    mock_websocket.send_json.reset_mock()
    mock_services["prompt_builder"].build_user_message_with_history.reset_mock()

    # Second query - user responds to clarification
    await manager.handle_query("USA", user_id)

    # Verify prompt builder was called with conversation history
    prompt_builder_calls = mock_services[
        "prompt_builder"
    ].build_user_message_with_history.call_args_list
    assert len(prompt_builder_calls) > 0

    # Get the conversation history passed to prompt builder
    _, kwargs = prompt_builder_calls[-1]
    conversation_history_passed = kwargs.get("conversation_history", [])

    print("\n=== Conversation history passed to LLM for second query ===")
    for idx, msg in enumerate(conversation_history_passed):
        print(f"  [{idx}] {msg['role']}: {msg['content'][:100]}...")

    # Verify the clarification message is included
    assert len(conversation_history_passed) >= 2, (
        "Expected at least 2 messages in history (original query + clarification)"
    )

    # Check that we have the user's first query
    user_messages = [m for m in conversation_history_passed if m["role"] == "user"]
    assert len(user_messages) >= 1, "Expected at least one user message in history"
    assert "phone" in user_messages[0]["content"].lower()

    # Check that we have the clarification question
    assistant_messages = [
        m for m in conversation_history_passed if m["role"] == "assistant"
    ]
    assert len(assistant_messages) >= 1, "Expected clarification message in history"
    # The clarification should ask for more details
    clarification_content = assistant_messages[-1]["content"].lower()
    assert (
        "which" in clarification_content or "city" in clarification_content
    ), f"Expected clarifying question, got: {assistant_messages[-1]['content']}"


@pytest.mark.asyncio
async def test_multiple_clarifications_preserve_context(mock_websocket, mock_services):
    """Test that multiple clarification rounds preserve full context."""

    with patch("src.response_manager.get_config", return_value=0.0):
        manager = ResponseManager(mock_websocket, is_authenticated=False)

    user_id = 11

    # First query
    await manager.handle_query("what the phone number of tlscontact?", user_id)

    # Second query (response to first clarification)
    mock_websocket.send_json.reset_mock()
    mock_services["prompt_builder"].build_user_message_with_history.reset_mock()
    await manager.handle_query("USA", user_id)

    # Third query (response to second clarification)
    mock_websocket.send_json.reset_mock()
    mock_services["prompt_builder"].build_user_message_with_history.reset_mock()
    await manager.handle_query("New York", user_id)

    # Get the conversation history for the third query
    prompt_builder_calls = mock_services[
        "prompt_builder"
    ].build_user_message_with_history.call_args_list
    _, kwargs = prompt_builder_calls[-1]
    conversation_history_passed = kwargs.get("conversation_history", [])

    print("\n=== Full conversation history after 3 turns ===")
    for idx, msg in enumerate(conversation_history_passed):
        role = msg["role"]
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        print(f"  [{idx}] {role}: {content}")

    # Should have all previous messages: query1, clarif1, query2, clarif2
    assert len(conversation_history_passed) >= 4, (
        f"Expected at least 4 messages (2 user queries + 2 clarifications), "
        f"got {len(conversation_history_passed)}"
    )

    # Verify we have both user messages
    user_messages = [m for m in conversation_history_passed if m["role"] == "user"]
    assert len(user_messages) >= 2, "Expected at least 2 user messages"

    # Verify we have both clarifications
    assistant_messages = [
        m for m in conversation_history_passed if m["role"] == "assistant"
    ]
    assert len(assistant_messages) >= 2, "Expected at least 2 clarification messages"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
