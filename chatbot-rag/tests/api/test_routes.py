"""Unit tests for REST API routes in src.api.routes."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

from src.api.routes import _validate_internal_key, chat_endpoint
from src.api.schemas import ChatRequest, ChatbotConfigPayload, ChatResponse


@pytest.fixture
def sample_chat_request():
    return ChatRequest(
        workspace_id="ws_001",
        chatbot_id="bot_001",
        session_id="sess_12345",
        message="Hello, what are your opening hours?",
        history=[],
        chatbot_config=ChatbotConfigPayload(
            llm_provider="groq",
            llm_model="mixtral-8x7b",
            system_prompt="Answer politely.",
            tone_preset="professional",
            company_name="Acme Corp",
        ),
    )


def test_validate_internal_key_valid(monkeypatch):
    """Test _validate_internal_key passes when header matches INTERNAL_API_KEY."""
    monkeypatch.setenv("INTERNAL_API_KEY", "secret_key_123")
    # Should not raise exception
    _validate_internal_key("secret_key_123")


def test_validate_internal_key_invalid(monkeypatch):
    """Test _validate_internal_key raises 401 when header does not match."""
    monkeypatch.setenv("INTERNAL_API_KEY", "secret_key_123")
    with pytest.raises(HTTPException) as exc_info:
        _validate_internal_key("wrong_key")
    assert exc_info.value.status_code == 401
    assert "Invalid internal API key" in exc_info.value.detail


def test_validate_internal_key_not_set(monkeypatch):
    """Test _validate_internal_key passes with warning when INTERNAL_API_KEY env var is not set."""
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    # Should not raise exception when env var missing
    _validate_internal_key("any_key")


@pytest.mark.asyncio
@patch("src.api.routes._validate_internal_key")
@patch("src.api.routes.AuthMiddleware")
@patch("src.api.routes.ChatEngineFactory")
async def test_chat_endpoint_happy_path_with_bearer_token(
    mock_factory, mock_auth_cls, mock_validate_key, sample_chat_request
):
    """Test chat_endpoint executes RAG pipeline and returns ChatResponse with valid Bearer token."""
    mock_auth = MagicMock()
    mock_auth.get_current_user.return_value = {"user_id": "user_456"}
    mock_auth_cls.return_value = mock_auth

    mock_engine = AsyncMock()
    mock_engine.process_message.return_value = {
        "response": "Our opening hours are 9am to 5pm.",
        "confidence": 0.95,
        "sources": [{"title": "Hours.pdf", "url": ""}],
        "clarification_question": None,
        "tokens": {"input": 10, "output": 20},
        "execution_time_ms": 150,
    }
    mock_factory.get_or_create.return_value = mock_engine

    response = await chat_endpoint(
        request=sample_chat_request,
        x_internal_api_key="valid_key",
        authorization="Bearer valid_jwt_token",
    )

    assert isinstance(response, ChatResponse)
    assert response.response == "Our opening hours are 9am to 5pm."
    assert response.confidence == 0.95
    assert len(response.sources) == 1
    assert response.execution_time_ms == 150

    mock_validate_key.assert_called_once_with("valid_key")
    mock_auth.get_current_user.assert_called_once_with("valid_jwt_token")
    mock_engine.process_message.assert_called_once_with(
        message="Hello, what are your opening hours?",
        history=[],
        user_id="user_456",
    )


@pytest.mark.asyncio
@patch("src.api.routes._validate_internal_key")
@patch("src.api.routes.AuthMiddleware")
@patch("src.api.routes.ChatEngineFactory")
async def test_chat_endpoint_jwt_error_falls_back_to_session_id(
    mock_factory, mock_auth_cls, mock_validate_key, sample_chat_request
):
    """Test chat_endpoint falls back to session_id when JWT contains an error dict."""
    mock_auth = MagicMock()
    mock_auth.get_current_user.return_value = {"error": "Token expired"}
    mock_auth_cls.return_value = mock_auth

    mock_engine = AsyncMock()
    mock_engine.process_message.return_value = {
        "response": "Fallback answer.",
        "confidence": 0.8,
        "sources": [],
        "clarification_question": None,
        "tokens": {"input": 0, "output": 0},
        "execution_time_ms": 50,
    }
    mock_factory.get_or_create.return_value = mock_engine

    response = await chat_endpoint(
        request=sample_chat_request,
        x_internal_api_key="valid_key",
        authorization="Bearer invalid_token",
    )

    assert response.response == "Fallback answer."
    # Should fall back to session_id ("sess_12345")
    mock_engine.process_message.assert_called_once_with(
        message="Hello, what are your opening hours?",
        history=[],
        user_id="sess_12345",
    )


@pytest.mark.asyncio
@patch("src.api.routes._validate_internal_key")
@patch("src.api.routes.ChatEngineFactory")
async def test_chat_endpoint_no_authorization_header(
    mock_factory, mock_validate_key, sample_chat_request
):
    """Test chat_endpoint uses session_id when no Authorization header is provided."""
    mock_engine = AsyncMock()
    mock_engine.process_message.return_value = {
        "response": "No auth response.",
        "confidence": 1.0,
        "sources": [],
        "clarification_question": None,
    }
    mock_factory.get_or_create.return_value = mock_engine

    response = await chat_endpoint(
        request=sample_chat_request,
        x_internal_api_key="valid_key",
        authorization=None,
    )

    assert response.response == "No auth response."
    mock_engine.process_message.assert_called_once_with(
        message="Hello, what are your opening hours?",
        history=[],
        user_id="sess_12345",
    )
