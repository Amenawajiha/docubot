"""Unit tests for TenantChatEngine in src.engine.tenant_chat_engine."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.config.chatbot_config import ChatbotConfig
from src.models import RetrievalResult, ConfidenceResult


@pytest.fixture
def sample_config():
    return ChatbotConfig(
        workspace_id="ws_101",
        chatbot_id="bot_202",
        session_id="sess_303",
        llm_provider="groq",
        llm_model="mixtral-8x7b",
        system_prompt="You are a helpful assistant.",
        tone_preset="friendly",
    )


@patch("src.engine.tenant_chat_engine.get_service_manager")
@patch("src.engine.tenant_chat_engine.TenantLLMOrchestrator")
@patch("src.engine.tenant_chat_engine.TenantPromptBuilder")
@patch("src.engine.tenant_chat_engine.VectorRetriever")
@patch("src.engine.tenant_chat_engine.TenantClarificationManager")
@patch("src.engine.tenant_chat_engine.TenantConversationRepository")
@patch("src.engine.tenant_chat_engine.ConversationManager")
@patch("src.engine.tenant_chat_engine.QueryRewriter")
def test_config_matches(
    mock_rewriter,
    mock_conv_mgr,
    mock_tenant_repo,
    mock_clarification,
    mock_retriever,
    mock_prompt_builder,
    mock_llm,
    mock_get_service_mgr,
    sample_config,
):
    """Test config_matches compares workspace_id, chatbot_id, llm settings, and prompts."""
    from src.engine.tenant_chat_engine import TenantChatEngine

    engine = TenantChatEngine(sample_config)

    # Identical config
    matching_config = ChatbotConfig(
        workspace_id="ws_101",
        chatbot_id="bot_202",
        session_id="sess_different",
        llm_provider="groq",
        llm_model="mixtral-8x7b",
        system_prompt="You are a helpful assistant.",
        tone_preset="friendly",
    )
    assert engine.config_matches(matching_config) is True

    # Differing system_prompt
    different_config = ChatbotConfig(
        workspace_id="ws_101",
        chatbot_id="bot_202",
        session_id="sess_303",
        llm_provider="groq",
        llm_model="mixtral-8x7b",
        system_prompt="Different prompt",
        tone_preset="friendly",
    )
    assert engine.config_matches(different_config) is False


@pytest.mark.asyncio
@patch("src.engine.tenant_chat_engine.get_service_manager")
@patch("src.engine.tenant_chat_engine.TenantLLMOrchestrator")
@patch("src.engine.tenant_chat_engine.TenantPromptBuilder")
@patch("src.engine.tenant_chat_engine.VectorRetriever")
@patch("src.engine.tenant_chat_engine.TenantClarificationManager")
@patch("src.engine.tenant_chat_engine.TenantConversationRepository")
@patch("src.engine.tenant_chat_engine.ConversationManager")
@patch("src.engine.tenant_chat_engine.QueryRewriter")
async def test_process_message_happy_path(
    mock_rewriter_cls,
    mock_conv_mgr_cls,
    mock_tenant_repo_cls,
    mock_clarification_cls,
    mock_retriever_cls,
    mock_prompt_builder_cls,
    mock_llm_cls,
    mock_get_service_mgr,
    sample_config,
):
    """Test process_message happy path execution flow."""
    from src.engine.tenant_chat_engine import TenantChatEngine

    # Mock dependencies
    mock_service_mgr = MagicMock()
    mock_get_service_mgr.return_value = mock_service_mgr

    engine = TenantChatEngine(sample_config)

    # Setup component behavior
    engine.query_rewriter.rewrite_query.return_value = "What is visa fee?"
    
    mock_result = RetrievalResult(
        content="The visa fee is 80 EUR.",
        metadata={"document_name": "Fees.pdf", "url": "https://example.com/fees.pdf"},
        relevance_score=0.9,
    )
    engine.vector_retriever.retrieve_with_reranking.return_value = [mock_result]
    engine.prompt_builder.build_user_message_with_history.return_value = [{"role": "user", "content": "test"}]
    engine.llm.send_messages.return_value = ("The Schengen visa fee is 80 EUR.", [-0.1])
    
    mock_conf = ConfidenceResult(
        retrieval_confidence=0.9,
        llm_confidence=0.9,
        overall_confidence=0.9,
        is_confident=True,
        confidence_breakdown={},
    )
    engine.confidence_scorer.run.return_value = mock_conf

    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    
    response = await engine.process_message(
        message="What is visa fee?",
        history=history,
        user_id="123",
    )

    assert response["response"] == "The Schengen visa fee is 80 EUR."
    assert response["confidence"] == 0.9
    assert len(response["sources"]) == 1
    assert response["sources"][0]["title"] == "Fees.pdf"
    assert response["clarification_question"] is None
    assert response["execution_time_ms"] >= 0


@pytest.mark.asyncio
@patch("src.engine.tenant_chat_engine.get_service_manager")
@patch("src.engine.tenant_chat_engine.TenantLLMOrchestrator")
@patch("src.engine.tenant_chat_engine.TenantPromptBuilder")
@patch("src.engine.tenant_chat_engine.VectorRetriever")
@patch("src.engine.tenant_chat_engine.TenantClarificationManager")
@patch("src.engine.tenant_chat_engine.TenantConversationRepository")
@patch("src.engine.tenant_chat_engine.ConversationManager")
@patch("src.engine.tenant_chat_engine.QueryRewriter")
async def test_process_message_retrieval_exception_fallback(
    mock_rewriter_cls,
    mock_conv_mgr_cls,
    mock_tenant_repo_cls,
    mock_clarification_cls,
    mock_retriever_cls,
    mock_prompt_builder_cls,
    mock_llm_cls,
    mock_get_service_mgr,
    sample_config,
):
    """Test process_message handles vector retrieval exceptions gracefully."""
    from src.engine.tenant_chat_engine import TenantChatEngine

    engine = TenantChatEngine(sample_config)
    engine.query_rewriter.rewrite_query.return_value = "query"
    engine.vector_retriever.retrieve_with_reranking.side_effect = Exception("Qdrant connection error")
    engine.prompt_builder.build_user_message_with_history.return_value = []
    engine.llm.send_messages.return_value = ("General answer.", [])
    
    mock_conf = ConfidenceResult(
        retrieval_confidence=0.0,
        llm_confidence=0.5,
        overall_confidence=0.2,
        is_confident=False,
        confidence_breakdown={},
    )
    engine.confidence_scorer.run.return_value = mock_conf

    response = await engine.process_message(
        message="query",
        history=[],
        user_id="user_abc_uuid",
    )

    assert response["response"] == "General answer."
    assert response["sources"] == []


@pytest.mark.asyncio
@patch("src.engine.tenant_chat_engine.get_service_manager")
@patch("src.engine.tenant_chat_engine.TenantLLMOrchestrator")
@patch("src.engine.tenant_chat_engine.TenantPromptBuilder")
@patch("src.engine.tenant_chat_engine.VectorRetriever")
@patch("src.engine.tenant_chat_engine.TenantClarificationManager")
@patch("src.engine.tenant_chat_engine.TenantConversationRepository")
@patch("src.engine.tenant_chat_engine.ConversationManager")
@patch("src.engine.tenant_chat_engine.QueryRewriter")
async def test_process_message_out_of_domain_unknown_fallback(
    mock_rewriter_cls,
    mock_conv_mgr_cls,
    mock_tenant_repo_cls,
    mock_clarification_cls,
    mock_retriever_cls,
    mock_prompt_builder_cls,
    mock_llm_cls,
    mock_get_service_mgr,
    sample_config,
):
    """Test out-of-domain question triggers TENANT_CONTACT_FALLBACK when LLM says unknown and retrieval_confidence < 0.1."""
    from src.engine.tenant_chat_engine import TenantChatEngine
    from src.llm.prompts import TENANT_CONTACT_FALLBACK

    engine = TenantChatEngine(sample_config)
    engine.query_rewriter.rewrite_query.return_value = "Random out of domain question"
    engine.vector_retriever.retrieve_with_reranking.return_value = []
    engine.prompt_builder.build_user_message_with_history.return_value = []
    engine.llm.send_messages.return_value = ("I don't know the answer to this.", [])

    mock_conf = ConfidenceResult(
        retrieval_confidence=0.05,  # < 0.1
        llm_confidence=0.1,
        overall_confidence=0.07,
        is_confident=False,
        confidence_breakdown={},
    )
    engine.confidence_scorer.run.return_value = mock_conf

    response = await engine.process_message(
        message="What is quantum physics?",
        history=[],
        user_id="user_999",
    )

    assert response["response"] == TENANT_CONTACT_FALLBACK
    assert response["clarification_question"] is None
