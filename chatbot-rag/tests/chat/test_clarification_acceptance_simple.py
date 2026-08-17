import pytest
from unittest.mock import AsyncMock, patch

from src.response_manager import ResponseManager
from src.models import ConfidenceResult


@pytest.mark.asyncio
async def test_clarification_sent_and_includes_recent_user_message():
    """When LLM indicates unknown and clarification is required, a clarification
    message should be sent and the refreshed conversation history should be used.
    """
    mock_ws = AsyncMock()

    manager = ResponseManager(fe_websocket=mock_ws, is_authenticated=False)

    user_id = 11
    query = "what the phone number of tlscontact ?"

    # initial history does not include the just-submitted user message
    initial_history = [
        {"role": "user", "content": "what the phone number of tlscontact ?"},
        {"role": "assistant", "content": "Could you let me know which country?", "metadata": {"type": "clarification"}},
    ]

    # refreshed history includes the saved user message (simulated)
    refreshed_history = [
        {"role": "user", "content": "what the phone number of tlscontact ?"},
        {"role": "assistant", "content": "Could you let me know which country?", "metadata": {"type": "clarification"}},
        {"role": "user", "content": "Anything is fine."},
    ]

    with patch.object(manager.vector_retriever, "retrieve_with_reranking", return_value=[]), \
         patch.object(manager.clarification_manager, "should_clarify", return_value=True), \
         patch.object(manager.clarification_manager, "generate_clarifying_question", return_value="Which city or country do you mean?"), \
         patch.object(manager.conversation_manager, "get_messages_for_llm", side_effect=[initial_history, refreshed_history]), \
         patch.object(manager.llm_orchestrator, "send_messages", return_value=("I don't know", [])), \
         patch.object(manager.confidence_scorer, "run", return_value=ConfidenceResult(
             retrieval_confidence=0.0,
             llm_confidence=0.1,
             overall_confidence=0.1,
             is_confident=False,
             confidence_breakdown={"retrieval": 0.0, "llm": 0.1},
         )):

        await manager.handle_query(query, user_id)

    # websocket should have been sent a clarification
    mock_ws.send_json.assert_called()
    sent = mock_ws.send_json.call_args[0][0]
    assert sent["type"] == "clarification"
    assert sent["content"] == "Which city or country do you mean?"
