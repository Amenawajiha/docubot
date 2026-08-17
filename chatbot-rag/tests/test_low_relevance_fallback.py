"""Test that low relevance contexts allow LLM to use its own knowledge."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.response_manager import ResponseManager
from src.models import RetrievalResult
from src.llm.prompts import CONTACT_FALLBACK


@pytest.mark.asyncio
async def test_greeting_with_low_relevance_uses_llm_knowledge():
    """Test that greetings work even when retrieval returns low relevance contexts."""
    
    # Mock WebSocket
    mock_websocket = AsyncMock()
    
    # Create ResponseManager with mocked websocket
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    
    # Mock low-relevance retrieval results (not related to greeting)
    low_relevance_contexts = [
        RetrievalResult(
            content="Phone number: + 1  5168357843 (USA)",
            metadata={"source": "Schengen Visa FAQs.docx", "chunk_type": "buffered"},
            relevance_score=0.05,
        ),
    ]
    
    # Mock LLM response for greeting
    mock_llm_send = Mock(return_value=("Hello! How can I help you with your Schengen visa application today?", []))
    
    # Mock vector retriever to return low-relevance contexts
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=low_relevance_contexts):
        with patch.object(manager.conversation_manager, 'get_messages_for_llm', return_value=[]):
            with patch.object(manager.conversation_manager, 'add_message'):
                with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
                    from src.models import ConfidenceResult
                    with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                        retrieval_confidence=0.05,
                        llm_confidence=0.5,
                        overall_confidence=0.185,
                        is_confident=False,
                        confidence_breakdown={}
                    )):
                        # Execute the query
                        await manager.handle_query(query="hi", user_id=11)
    
    # Verify LLM was called (not skipped)
    mock_llm_send.assert_called_once()
    
    # Verify websocket was called with LLM response (NOT fallback)
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    
    assert call_args["type"] == "answer"
    assert call_args["content"] != CONTACT_FALLBACK
    assert "help@schengenvisaitinerary.com" not in call_args["content"]


@pytest.mark.asyncio
async def test_low_relevance_unknown_response_triggers_fallback():
    """Test that when LLM says 'I don't know' with low relevance, CONTACT_FALLBACK is used."""
    
    # Mock WebSocket
    mock_websocket = AsyncMock()
    
    # Create ResponseManager with mocked websocket
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    
    # Mock low-relevance retrieval results (all below 0.7 threshold)
    low_relevance_contexts = [
        RetrievalResult(
            content="Phone number: + 1  5168357843 (USA)",
            metadata={"source": "Schengen Visa FAQs.docx", "chunk_type": "buffered"},
            relevance_score=0.05,
        ),
        RetrievalResult(
            content="Please call on our whatsapp number +15168357843",
            metadata={"source": "Schengen Visa FAQs.docx", "chunk_type": "buffered"},
            relevance_score=0.03,
        ),
    ]
    
    # Mock LLM to say "I don't know" (triggering clarification/fallback logic)
    mock_llm_send = Mock(return_value=("I don't know!", []))
    
    # Mock vector retriever to return low-relevance contexts
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=low_relevance_contexts):
        with patch.object(manager.conversation_manager, 'get_messages_for_llm', return_value=[]):
            with patch.object(manager.conversation_manager, 'add_message'):
                with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
                    from src.models import ConfidenceResult
                    # Mock clarification manager to NOT clarify (return fallback instead)
                    with patch.object(manager.clarification_manager, 'should_clarify', return_value=False):
                        with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                            retrieval_confidence=0.04,
                            llm_confidence=0.5,
                            overall_confidence=0.178,
                            is_confident=False,
                            confidence_breakdown={}
                        )):
                            # Execute the query
                            await manager.handle_query(
                                query="What is the phone number of TLSContact?",
                                user_id=11
                            )
    
    # Since LLM said "I don't know", has low confidence, and no relevant context,
    # the system should replace the uncertain response with CONTACT_FALLBACK
    mock_llm_send.assert_called_once()
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    
    assert call_args["type"] == "answer"
    # The response should be CONTACT_FALLBACK (replacing "I don't know")
    assert call_args["content"] == CONTACT_FALLBACK


@pytest.mark.asyncio
async def test_high_relevance_calls_llm():
    """Test that when contexts have high relevance, LLM is called normally."""
    
    # Mock WebSocket
    mock_websocket = AsyncMock()
    
    # Create ResponseManager with mocked websocket
    manager = ResponseManager(fe_websocket=mock_websocket, is_authenticated=False)
    
    # Mock high-relevance retrieval results (above 0.7 threshold)
    high_relevance_contexts = [
        RetrievalResult(
            content="TLSContact France phone: +33 1 23 45 67 89",
            metadata={"source": "TLSContact.docx", "chunk_type": "buffered"},
            relevance_score=0.85,
        ),
    ]
    
    # Mock vector retriever to return high-relevance contexts
    mock_llm_send = Mock(return_value=("TLSContact France: +33 1 23 45 67 89", []))
    
    with patch.object(manager.vector_retriever, 'retrieve_with_reranking', return_value=high_relevance_contexts):
        # Mock conversation manager methods
        with patch.object(manager.conversation_manager, 'get_messages_for_llm', return_value=[]):
            with patch.object(manager.conversation_manager, 'add_message'):
                # Mock LLM to return a response
                with patch.object(manager.llm_orchestrator, 'send_messages', mock_llm_send):
                    # Mock confidence scorer
                    from src.models import ConfidenceResult
                    with patch.object(manager.confidence_scorer, 'run', return_value=ConfidenceResult(
                        retrieval_confidence=0.85,
                        llm_confidence=0.5,
                        overall_confidence=0.745,
                        is_confident=True,
                        confidence_breakdown={}
                    )):
                        # Execute the query
                        await manager.handle_query(
                            query="What is the phone number of TLSContact?",
                            user_id=11
                        )
    
    # Verify LLM was called (not fallback)
    mock_llm_send.assert_called_once()
    
    # Verify websocket was called with LLM response (not fallback)
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    
    assert call_args["type"] == "answer"
    assert call_args["content"] != CONTACT_FALLBACK
    assert "TLSContact" in call_args["content"]
