"""Unit tests for ChatEngineFactory in src.engine.chat_engine_factory."""

import pytest
from unittest.mock import MagicMock, patch

from src.engine.chat_engine_factory import ChatEngineFactory
from src.config.chatbot_config import ChatbotConfig


@pytest.fixture(autouse=True)
def reset_factory_instances():
    """Reset factory cache before and after each test."""
    ChatEngineFactory._instances.clear()
    yield
    ChatEngineFactory._instances.clear()


def make_sample_config(
    workspace_id="ws_1",
    chatbot_id="bot_1",
    session_id="sess_1",
    llm_provider="groq",
    llm_model="mixtral-8x7b",
    system_prompt="Test Prompt",
):
    return ChatbotConfig(
        workspace_id=workspace_id,
        chatbot_id=chatbot_id,
        session_id=session_id,
        llm_provider=llm_provider,
        llm_model=llm_model,
        system_prompt=system_prompt,
    )


@patch("src.engine.chat_engine_factory.TenantChatEngine")
def test_get_or_create_creates_new_instance(mock_tenant_engine_cls):
    """Test get_or_create instantiates a new engine on initial request."""
    mock_engine = MagicMock()
    mock_tenant_engine_cls.return_value = mock_engine

    config = make_sample_config()
    engine = ChatEngineFactory.get_or_create(config)

    assert engine == mock_engine
    mock_tenant_engine_cls.assert_called_once_with(config)
    assert ChatEngineFactory._instances["ws_1:bot_1"] == mock_engine


@patch("src.engine.chat_engine_factory.TenantChatEngine")
def test_get_or_create_fast_path_cache_hit(mock_tenant_engine_cls):
    """Test get_or_create fast path returns cached engine if config matches."""
    mock_engine = MagicMock()
    mock_engine.config_matches.return_value = True

    key = "ws_1:bot_1"
    ChatEngineFactory._instances[key] = mock_engine

    config = make_sample_config()
    engine = ChatEngineFactory.get_or_create(config)

    assert engine == mock_engine
    mock_engine.config_matches.assert_called_once_with(config)
    mock_tenant_engine_cls.assert_not_called()


@patch("src.engine.chat_engine_factory.TenantChatEngine")
def test_get_or_create_config_mismatch_recreates_engine(mock_tenant_engine_cls):
    """Test get_or_create creates a new engine if existing cached config does not match."""
    old_engine = MagicMock()
    old_engine.config_matches.return_value = False

    new_engine = MagicMock()
    mock_tenant_engine_cls.return_value = new_engine

    key = "ws_1:bot_1"
    ChatEngineFactory._instances[key] = old_engine

    config = make_sample_config(system_prompt="Updated System Prompt")
    engine = ChatEngineFactory.get_or_create(config)

    assert engine == new_engine
    assert ChatEngineFactory._instances[key] == new_engine
    mock_tenant_engine_cls.assert_called_once_with(config)


@patch("src.engine.chat_engine_factory.TenantChatEngine")
def test_get_or_create_slow_path_double_check(mock_tenant_engine_cls):
    """Test get_or_create slow path double check returns cached instance if another thread set it."""
    mock_engine = MagicMock()
    mock_engine.config_matches.return_value = True

    config = make_sample_config()
    
    # Simulate another thread acquiring lock and setting cache right before slow-path check
    class MockLock:
        def __enter__(self):
            ChatEngineFactory._instances["ws_1:bot_1"] = mock_engine
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch.object(ChatEngineFactory, "_lock", new=MockLock()):
        engine = ChatEngineFactory.get_or_create(config)
        assert engine == mock_engine
        mock_tenant_engine_cls.assert_not_called()


def test_invalidate_removes_existing_key():
    """Test invalidate removes the engine key from cache."""
    mock_engine = MagicMock()
    key = "ws_100:bot_200"
    ChatEngineFactory._instances[key] = mock_engine

    assert key in ChatEngineFactory._instances
    ChatEngineFactory.invalidate("ws_100", "bot_200")
    assert key not in ChatEngineFactory._instances


def test_invalidate_non_existent_key_does_not_error():
    """Test invalidate handles non-existent key gracefully without raising KeyError."""
    ChatEngineFactory.invalidate("non_existent_ws", "non_existent_bot")
    assert "non_existent_ws:non_existent_bot" not in ChatEngineFactory._instances
