"""
Robust RAG pipeline tests for all critical scenarios.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.response_manager import ResponseManager
from src.models import RetrievalResult, ConfidenceResult
from src.llm.prompts import CONTACT_FALLBACK

@pytest.mark.asyncio
async def test_no_relevant_chunks_llm_uses_knowledge():
    """If no chunks above low_cutoff, LLM should answer from its knowledge if confident."""
    mock_websocket = AsyncMock()
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    # All chunks below 0.3
    low_contexts = [
        RetrievalResult(content="irrelevant", metadata={}, relevance_score=0.1),
        RetrievalResult(content="noise", metadata={}, relevance_score=0.2),
    ]
    # LLM is confident in its knowledge
    mock_llm_send = Mock(return_value=("General Schengen info from LLM knowledge", [0.0, 0.0]))
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=low_contexts):
        with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
            with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                retrieval_confidence=0.15, llm_confidence=0.9, overall_confidence=0.7, is_confident=True, confidence_breakdown={}
            )):
                await manager.handle_query(query="What is a Schengen visa?", user_id=1)
    mock_llm_send.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "answer"
    assert "Schengen" in call_args["content"]
    assert CONTACT_FALLBACK not in call_args["content"]

@pytest.mark.asyncio
async def test_only_relevant_chunks_sent():
    """Only chunks above low_cutoff are sent as context."""
    mock_websocket = AsyncMock()
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    contexts = [
        RetrievalResult(content="relevant info", metadata={}, relevance_score=0.5),
        RetrievalResult(content="irrelevant", metadata={}, relevance_score=0.1),
    ]
    mock_llm_send = Mock(return_value=("Answer with relevant info", [0.0, 0.0]))
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=contexts):
        with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
            with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                retrieval_confidence=0.5, llm_confidence=0.8, overall_confidence=0.65, is_confident=True, confidence_breakdown={}
            )):
                await manager.handle_query(query="Give me info", user_id=2)
    args, kwargs = mock_llm_send.call_args
    # Only the relevant chunk should be in the context
    context_chunks = [m for m in args[0] if m["role"] == "user"]
    assert any("relevant info" in m["content"] for m in context_chunks)
    assert not any("irrelevant" in m["content"] for m in context_chunks)

@pytest.mark.asyncio
async def test_ambiguous_query_triggers_clarification():
    """Ambiguous query should trigger clarification."""
    mock_websocket = AsyncMock()
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    contexts = [RetrievalResult(content="", metadata={}, relevance_score=0.0)]
    # LLM says "I don't know" (ambiguous)
    mock_llm_send = Mock(return_value=("I don't know!", [0.0, 0.0]))
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=contexts):
        with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
            with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                retrieval_confidence=0.0, llm_confidence=0.5, overall_confidence=0.2, is_confident=False, confidence_breakdown={}
            )):
                with patch.object(manager.clarification_manager, 'should_clarify', return_value=True):
                    with patch.object(manager.clarification_manager, 'generate_clarifying_question', return_value="What do you mean by 'itinerary'?"):
                        await manager.handle_query(query="How much?", user_id=3)
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "clarification"
    assert "What do you mean" in call_args["content"]

@pytest.mark.asyncio
async def test_llm_not_confident_no_answer():
    """If LLM is not confident and no context, should not answer (should fallback)."""
    mock_websocket = AsyncMock()
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    contexts = []
    mock_llm_send = Mock(return_value=("I don't know!", [0.0, 0.0]))
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=contexts):
        with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
            with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                retrieval_confidence=0.0, llm_confidence=0.1, overall_confidence=0.1, is_confident=False, confidence_breakdown={}
            )):
                with patch.object(manager.clarification_manager, 'should_clarify', return_value=False):
                    await manager.handle_query(query="What is the secret code?", user_id=4)
    call_args = mock_websocket.send_json.call_args[0][0]
    # Should fallback to CONTACT_FALLBACK
    assert call_args["type"] == "answer"
    assert CONTACT_FALLBACK in call_args["content"]

@pytest.mark.asyncio
async def test_conversation_history_included():
    """Conversation history is included if present."""
    mock_websocket = AsyncMock()
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    contexts = [RetrievalResult(content="relevant", metadata={}, relevance_score=0.8)]
    mock_llm_send = Mock(return_value=("Answer with history", [0.0, 0.0]))
    fake_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=contexts):
        with patch.object(manager.conversation_manager, 'get_messages_for_llm', return_value=fake_history):
            with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
                with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                    retrieval_confidence=0.8, llm_confidence=0.8, overall_confidence=0.8, is_confident=True, confidence_breakdown={}
                )):
                    await manager.handle_query(query="Tell me more", user_id=5)
    args, kwargs = mock_llm_send.call_args
    # History should be present in the messages
    assert any(m.get("role") == "user" and "Hi" in m.get("content", "") for m in args[0])
    assert any(m.get("role") == "assistant" and "Hello" in m.get("content", "") for m in args[0])
