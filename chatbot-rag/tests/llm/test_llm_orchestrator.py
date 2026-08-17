"""
Comprehensive unit tests for LLMOrchestrator.

This test suite covers:
- Initialization and configuration
- Message sending (send_message)
- Pre-built message sending (send_messages)
- Streaming responses (send_message_stream)
- Logprobs extraction
- Error handling
- Edge cases and boundary conditions
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.llm.llm_orchestrator import LLMOrchestrator
from src.utils.exceptions import LLMException


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """
    Mock configuration values.
    
    Testing Concept: Mock configuration loading
    """
    config_values = {
        "model_name": "llama-3.1-8b-instant",
        "base_url": "https://api.groq.com/openai/v1",
        "temperature": 0.7,
        "max_tokens": 1024,
        "enable_logprobs": False,
        "logprobs_top_k": 5,
    }
    
    with patch("src.llm.llm_orchestrator.get_config_section") as mock:
        mock.return_value = config_values
        yield mock


@pytest.fixture
def mock_config_with_logprobs():
    """
    Mock configuration with logprobs enabled.
    
    Testing Concept: Mock configuration variant
    """
    config_values = {
        "model_name": "llama-3.1-8b-instant",
        "base_url": "https://api.groq.com/openai/v1",
        "temperature": 0.7,
        "max_tokens": 1024,
        "enable_logprobs": True,
        "logprobs_top_k": 5,
    }
    
    with patch("src.llm.llm_orchestrator.get_config_section") as mock:
        mock.return_value = config_values
        yield mock


@pytest.fixture
def mock_env():
    """
    Mock environment variables.
    
    Testing Concept: Mock environment
    """
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-api-key-12345"}):
        yield


@pytest.fixture
def mock_logger():
    """
    Mock logger to avoid actual logging during tests.
    
    Testing Concept: Mock logging
    """
    with patch("src.llm.llm_orchestrator.logger") as mock:
        yield mock


@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI client.
    
    Testing Concept: Mock external API client
    """
    mock_client = MagicMock()
    
    # Mock successful completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a test response from the LLM."
    mock_response.choices[0].logprobs = None
    
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_openai_client_with_logprobs():
    """
    Mock OpenAI client with logprobs.
    
    Testing Concept: Mock API response with additional data
    """
    mock_client = MagicMock()
    
    # Mock logprobs data
    mock_token_1 = MagicMock()
    mock_token_1.logprob = -0.5
    mock_token_2 = MagicMock()
    mock_token_2.logprob = -1.2
    mock_token_3 = MagicMock()
    mock_token_3.logprob = -0.8
    
    mock_logprobs = MagicMock()
    mock_logprobs.content = [mock_token_1, mock_token_2, mock_token_3]
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response with logprobs."
    mock_response.choices[0].logprobs = mock_logprobs
    
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_prompt_builder():
    """
    Mock PromptBuilder.
    
    Testing Concept: Mock prompt building
    """
    mock_builder = MagicMock()
    
    # Mock build_user_conversation_messages
    mock_builder.build_user_conversation_messages.return_value = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Test prompt"}
    ]
    
    return mock_builder


@pytest.fixture
def llm_orchestrator(mock_config, mock_env, mock_logger, mock_openai_client, mock_prompt_builder):
    """
    Create LLMOrchestrator with mocked dependencies.
    
    Testing Concept: Fixture with dependency injection
    """
    with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
        mock_openai_class.return_value = mock_openai_client
        
        with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
            mock_builder_class.return_value = mock_prompt_builder
            
            orchestrator = LLMOrchestrator()
            orchestrator.client = mock_openai_client
            orchestrator.prompt_builder = mock_prompt_builder
            
            return orchestrator


@pytest.fixture
def mock_stream_response():
    """
    Mock streaming response from OpenAI.
    
    Testing Concept: Mock streaming data
    """
    # Create mock stream chunks
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Hello "
    
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "world!"
    
    chunk3 = MagicMock()
    chunk3.choices = [MagicMock()]
    chunk3.choices[0].delta.content = None  # End of stream
    
    return [chunk1, chunk2, chunk3]


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestLLMOrchestratorInitialization:
    """Test LLMOrchestrator initialization."""
    
    def test_initialization_loads_config(self, mock_env, mock_logger):
        """
        Test that configuration is loaded during initialization.
        
        Testing Concept: Verify configuration loading
        """
        with patch("src.llm.llm_orchestrator.get_config_section") as mock_config:
            mock_config.return_value = {
                "model_name": "test-model",
                "base_url": "https://test.api.com",
                "temperature": 0.5,
                "max_tokens": 512,
            }
            
            with patch("src.llm.llm_orchestrator.OpenAI"):
                with patch("src.llm.llm_orchestrator.PromptBuilder"):
                    orchestrator = LLMOrchestrator()
                    
                    mock_config.assert_called_once_with("llm")
                    assert orchestrator.model_name == "test-model"
    
    def test_initialization_creates_openai_client(self, mock_config, mock_env, mock_logger):
        """
        Test that OpenAI client is created with correct parameters.
        
        Testing Concept: Verify dependency creation
        """
        with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
            with patch("src.llm.llm_orchestrator.PromptBuilder"):
                orchestrator = LLMOrchestrator()
                
                # Verify OpenAI was instantiated
                mock_openai_class.assert_called_once()
                
                # Verify correct parameters
                call_kwargs = mock_openai_class.call_args[1]
                assert call_kwargs["api_key"] == "test-api-key-12345"
                assert call_kwargs["base_url"] == "https://api.groq.com/openai/v1"
    
    def test_initialization_creates_prompt_builder(self, mock_config, mock_env, mock_logger):
        """
        Test that PromptBuilder is created.
        
        Testing Concept: Verify dependency creation
        """
        with patch("src.llm.llm_orchestrator.OpenAI"):
            with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
                orchestrator = LLMOrchestrator()
                
                mock_builder_class.assert_called_once()
                assert orchestrator.prompt_builder is not None
    
    def test_initialization_with_missing_api_key(self, mock_config, mock_logger):
        """
        Test initialization when API key is missing.
        
        Testing Concept: Test missing environment variable
        """
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
                with patch("src.llm.llm_orchestrator.PromptBuilder"):
                    orchestrator = LLMOrchestrator()
                    
                    # Should still create client, but with None API key
                    call_kwargs = mock_openai_class.call_args[1]
                    assert call_kwargs["api_key"] is None


# ============================================================================
# TEST CLASS: Send Message - Happy Path
# ============================================================================


class TestSendMessageHappyPath:
    """Test send_message functionality."""
    
    def test_send_message_returns_tuple(self, llm_orchestrator):
        """
        Test that send_message returns a tuple.
        
        Testing Concept: Test return type
        """
        result = llm_orchestrator.send_message("Test prompt")
        
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_send_message_returns_response_text(self, llm_orchestrator):
        """
        Test that send_message returns response text.
        
        Testing Concept: Test return value
        """
        response_text, logprobs = llm_orchestrator.send_message("What is AI?")
        
        assert isinstance(response_text, str)
        assert response_text == "This is a test response from the LLM."
    
    def test_send_message_calls_prompt_builder(self, llm_orchestrator):
        """
        Test that prompt builder is called to build messages.
        
        Testing Concept: Verify dependency interaction
        """
        llm_orchestrator.send_message("Test prompt")
        
        llm_orchestrator.prompt_builder.build_user_conversation_messages.assert_called_once_with(
            "Test prompt"
        )
    
    def test_send_message_calls_send_messages(self, llm_orchestrator):
        """
        Test that send_message delegates to send_messages.
        
        Testing Concept: Test method delegation
        """
        with patch.object(llm_orchestrator, 'send_messages') as mock_send_messages:
            mock_send_messages.return_value = ("Response", None)
            
            result = llm_orchestrator.send_message("Test")
            
            # Verify send_messages was called with built messages
            mock_send_messages.assert_called_once()
            assert result == ("Response", None)
    
    def test_send_message_with_empty_prompt(self, llm_orchestrator):
        """
        Test send_message with empty prompt.
        
        Testing Concept: Test empty input
        """
        response_text, logprobs = llm_orchestrator.send_message("")
        
        # Should still work (API handles empty prompts)
        assert isinstance(response_text, str)
    
    def test_send_message_with_long_prompt(self, llm_orchestrator):
        """
        Test send_message with very long prompt.
        
        Testing Concept: Test large input
        """
        long_prompt = "Test " * 1000
        
        response_text, logprobs = llm_orchestrator.send_message(long_prompt)
        
        assert isinstance(response_text, str)
    
    def test_send_message_without_logprobs(self, llm_orchestrator):
        """
        Test that logprobs is None when disabled.
        
        Testing Concept: Test conditional feature
        """
        response_text, logprobs = llm_orchestrator.send_message("Test")
        
        assert logprobs is None


# ============================================================================
# TEST CLASS: Send Messages - Happy Path
# ============================================================================


class TestSendMessagesHappyPath:
    """Test send_messages functionality."""
    
    def test_send_messages_returns_tuple(self, llm_orchestrator):
        """
        Test that send_messages returns a tuple.
        
        Testing Concept: Test return type
        """
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"}
        ]
        
        result = llm_orchestrator.send_messages(messages)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_send_messages_calls_openai_api(self, llm_orchestrator):
        """
        Test that OpenAI API is called with correct parameters.
        
        Testing Concept: Verify API call
        """
        messages = [{"role": "user", "content": "Test"}]
        
        llm_orchestrator.send_messages(messages)
        
        # Verify API was called
        llm_orchestrator.client.chat.completions.create.assert_called_once()
        
        # Verify parameters
        call_kwargs = llm_orchestrator.client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "llama-3.1-8b-instant"
        assert call_kwargs["messages"] == messages
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 1024
        assert "logprobs" not in call_kwargs  # Disabled by default
    
    def test_send_messages_extracts_response_text(self, llm_orchestrator):
        """
        Test that response text is correctly extracted.
        
        Testing Concept: Test data extraction
        """
        messages = [{"role": "user", "content": "Hello"}]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert response_text == "This is a test response from the LLM."
    
    def test_send_messages_with_empty_list(self, llm_orchestrator):
        """
        Test send_messages with empty message list.
        
        Testing Concept: Test empty input
        """
        response_text, logprobs = llm_orchestrator.send_messages([])
        
        # Should still make API call (API may reject, but orchestrator handles it)
        assert isinstance(response_text, str)
    
    def test_send_messages_with_multiple_messages(self, llm_orchestrator):
        """
        Test send_messages with multiple messages.
        
        Testing Concept: Test normal conversation flow
        """
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is..."},
            {"role": "user", "content": "Tell me more"}
        ]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert isinstance(response_text, str)
        
        # Verify all messages were passed
        call_kwargs = llm_orchestrator.client.chat.completions.create.call_args[1]
        assert len(call_kwargs["messages"]) == 4
    
    def test_send_messages_logs_response(self, llm_orchestrator, mock_logger):
        """
        Test that response is logged.
        
        Testing Concept: Test logging
        """
        messages = [{"role": "user", "content": "Test"}]
        
        llm_orchestrator.send_messages(messages)
        
        # Verify debug logging
        mock_logger.debug.assert_called_with(
            "LLM RESPONSE: %s",
            "This is a test response from the LLM."
        )


# ============================================================================
# TEST CLASS: Send Messages with Logprobs
# ============================================================================


class TestSendMessagesWithLogprobs:
    """Test send_messages with logprobs enabled."""
    
    def test_send_messages_with_logprobs_enabled(
        self, mock_config_with_logprobs, mock_env, mock_logger,
        mock_openai_client_with_logprobs, mock_prompt_builder
    ):
        """
        Test that logprobs are included when enabled.
        
        Testing Concept: Test conditional API parameters
        """
        with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
            mock_openai_class.return_value = mock_openai_client_with_logprobs
            
            with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
                mock_builder_class.return_value = mock_prompt_builder
                
                orchestrator = LLMOrchestrator()
                orchestrator.client = mock_openai_client_with_logprobs
                
                messages = [{"role": "user", "content": "Test"}]
                response_text, logprobs = orchestrator.send_messages(messages)
                
                # Verify logprobs parameters were added
                call_kwargs = mock_openai_client_with_logprobs.chat.completions.create.call_args[1]
                assert call_kwargs["logprobs"] is True
                assert call_kwargs["top_logprobs"] == 5
    
    def test_send_messages_extracts_logprobs(
        self, mock_config_with_logprobs, mock_env, mock_logger,
        mock_openai_client_with_logprobs, mock_prompt_builder
    ):
        """
        Test that logprobs are correctly extracted.
        
        Testing Concept: Test data extraction with logprobs
        """
        with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
            mock_openai_class.return_value = mock_openai_client_with_logprobs
            
            with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
                mock_builder_class.return_value = mock_prompt_builder
                
                orchestrator = LLMOrchestrator()
                orchestrator.client = mock_openai_client_with_logprobs
                
                messages = [{"role": "user", "content": "Test"}]
                response_text, logprobs = orchestrator.send_messages(messages)
                
                # Verify logprobs were extracted
                assert logprobs is not None
                assert isinstance(logprobs, list)
                assert len(logprobs) == 3
                assert logprobs == [-0.5, -1.2, -0.8]
    
    def test_send_messages_with_logprobs_none_in_response(
        self, mock_config_with_logprobs, mock_env, mock_logger,
        mock_prompt_builder
    ):
        """
        Test handling when logprobs is None in response despite being enabled.
        
        Testing Concept: Test edge case response
        """
        # Create client with logprobs=None
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.choices[0].logprobs = None  # No logprobs in response
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
            mock_openai_class.return_value = mock_client
            
            with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
                mock_builder_class.return_value = mock_prompt_builder
                
                orchestrator = LLMOrchestrator()
                orchestrator.client = mock_client
                
                messages = [{"role": "user", "content": "Test"}]
                response_text, logprobs = orchestrator.send_messages(messages)
                
                # Should handle gracefully
                assert logprobs is None


# ============================================================================
# TEST CLASS: Send Message Stream - Happy Path
# ============================================================================


class TestSendMessageStreamHappyPath:
    """Test send_message_stream functionality."""
    
    @pytest.mark.asyncio
    async def test_send_message_stream_returns_async_iterator(self, llm_orchestrator):
        """
        Test that send_message_stream returns an async iterator.
        
        Testing Concept: Test async return type
        """
        result = llm_orchestrator.send_message_stream("Test prompt")
        
        # Should be async generator
        assert hasattr(result, '__aiter__')
    
    @pytest.mark.asyncio
    async def test_send_message_stream_yields_chunks(
        self, llm_orchestrator, mock_stream_response
    ):
        """
        Test that streaming yields text chunks.
        
        Testing Concept: Test async iteration
        """
        # Mock streaming response
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        chunks = []
        async for chunk in llm_orchestrator.send_message_stream("Test"):
            chunks.append(chunk)
        
        # Should have received 2 chunks (3rd has None content)
        assert len(chunks) == 2
        assert chunks[0] == "Hello "
        assert chunks[1] == "world!"
    
    @pytest.mark.asyncio
    async def test_send_message_stream_calls_prompt_builder(self, llm_orchestrator):
        """
        Test that prompt builder is called.
        
        Testing Concept: Verify dependency interaction in async
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter([])
        
        async for _ in llm_orchestrator.send_message_stream("Test"):
            pass
        
        llm_orchestrator.prompt_builder.build_user_conversation_messages.assert_called_once_with(
            "Test"
        )
    
    @pytest.mark.asyncio
    async def test_send_message_stream_calls_api_with_stream_true(
        self, llm_orchestrator, mock_stream_response
    ):
        """
        Test that API is called with stream=True.
        
        Testing Concept: Test API parameter for streaming
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        async for _ in llm_orchestrator.send_message_stream("Test"):
            pass
        
        # Verify stream=True was passed
        call_kwargs = llm_orchestrator.client.chat.completions.create.call_args[1]
        assert call_kwargs["stream"] is True
    
    @pytest.mark.asyncio
    async def test_send_message_stream_logs_input_messages(
        self, llm_orchestrator, mock_logger, mock_stream_response
    ):
        """
        Test that input messages are logged.
        
        Testing Concept: Test logging in async
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        async for _ in llm_orchestrator.send_message_stream("Test"):
            pass
        
        # Verify debug logging for input
        mock_logger.debug.assert_any_call(
            "DEBUG LLM STREAM INPUT MESSAGES: %s",
            llm_orchestrator.prompt_builder.build_user_conversation_messages.return_value
        )
    
    @pytest.mark.asyncio
    async def test_send_message_stream_logs_chunks(
        self, llm_orchestrator, mock_logger, mock_stream_response
    ):
        """
        Test that each chunk is logged.
        
        Testing Concept: Test logging per iteration
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        async for _ in llm_orchestrator.send_message_stream("Test"):
            pass
        
        # Verify debug logging for chunks
        mock_logger.debug.assert_any_call("DEBUG LLM STREAM CHUNK: %s", "Hello ")
        mock_logger.debug.assert_any_call("DEBUG LLM STREAM CHUNK: %s", "world!")
    
    @pytest.mark.asyncio
    async def test_send_message_stream_skips_none_content(
        self, llm_orchestrator, mock_stream_response
    ):
        """
        Test that chunks with None content are skipped.
        
        Testing Concept: Test filtering in async iteration
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        chunks = []
        async for chunk in llm_orchestrator.send_message_stream("Test"):
            chunks.append(chunk)
        
        # Should only have non-None chunks
        assert all(chunk is not None for chunk in chunks)
        assert len(chunks) == 2
    
    @pytest.mark.asyncio
    async def test_send_message_stream_with_empty_prompt(
        self, llm_orchestrator, mock_stream_response
    ):
        """
        Test streaming with empty prompt.
        
        Testing Concept: Test empty input in async
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        chunks = []
        async for chunk in llm_orchestrator.send_message_stream(""):
            chunks.append(chunk)
        
        # Should still work
        assert len(chunks) >= 0
    
    @pytest.mark.asyncio
    async def test_send_message_stream_with_no_chunks(self, llm_orchestrator):
        """
        Test streaming when API returns no chunks.
        
        Testing Concept: Test empty iteration
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter([])
        
        chunks = []
        async for chunk in llm_orchestrator.send_message_stream("Test"):
            chunks.append(chunk)
        
        assert len(chunks) == 0


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling for all methods."""
    
    def test_send_messages_raises_llm_exception_on_api_error(self, llm_orchestrator):
        """
        Test that LLMException is raised when API call fails.
        
        Testing Concept: Test exception handling
        """
        # Mock API to raise exception
        llm_orchestrator.client.chat.completions.create.side_effect = Exception(
            "API connection failed"
        )
        
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(LLMException, match="AI API call failed"):
            llm_orchestrator.send_messages(messages)
    
    def test_send_message_raises_llm_exception_on_api_error(self, llm_orchestrator):
        """
        Test that send_message propagates LLMException.
        
        Testing Concept: Test exception propagation
        """
        # Mock send_messages to raise exception
        with patch.object(llm_orchestrator, 'send_messages') as mock_send_messages:
            mock_send_messages.side_effect = LLMException("API failed")
            
            with pytest.raises(LLMException, match="API failed"):
                llm_orchestrator.send_message("Test")
    
    @pytest.mark.asyncio
    async def test_send_message_stream_raises_llm_exception_on_error(
        self, llm_orchestrator
    ):
        """
        Test that streaming raises LLMException on error.
        
        Testing Concept: Test async exception handling
        """
        # Mock API to raise exception
        llm_orchestrator.client.chat.completions.create.side_effect = Exception(
            "Streaming failed"
        )
        
        with pytest.raises(LLMException, match="AI API streaming failed"):
            async for _ in llm_orchestrator.send_message_stream("Test"):
                pass
    
    def test_send_messages_wraps_original_exception(self, llm_orchestrator):
        """
        Test that original exception is wrapped in LLMException.
        
        Testing Concept: Test exception chaining
        """
        original_error = ValueError("Invalid model name")
        llm_orchestrator.client.chat.completions.create.side_effect = original_error
        
        messages = [{"role": "user", "content": "Test"}]
        
        try:
            llm_orchestrator.send_messages(messages)
        except LLMException as e:
            # Verify original exception is preserved
            assert e.__cause__ == original_error
            assert "Invalid model name" in str(e)
    
    def test_send_messages_with_malformed_response(self, llm_orchestrator):
        """
        Test handling of malformed API response.
        
        Testing Concept: Test unexpected response structure
        """
        # Mock malformed response (missing choices)
        mock_response = MagicMock()
        mock_response.choices = []
        llm_orchestrator.client.chat.completions.create.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(Exception):  # Will raise IndexError or similar
            llm_orchestrator.send_messages(messages)
    
    def test_send_messages_with_none_content_in_response(self, llm_orchestrator):
        """
        Test handling when response content is None.
        
        Testing Concept: Test None value in response
        """
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].logprobs = None
        llm_orchestrator.client.chat.completions.create.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test"}]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        # Should return None (or handle gracefully)
        assert response_text is None


# ============================================================================
# TEST CLASS: Edge Cases and Boundary Conditions
# ============================================================================


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""
    
    def test_send_messages_with_single_message(self, llm_orchestrator):
        """
        Test with single message.
        
        Testing Concept: Test minimum valid input
        """
        messages = [{"role": "user", "content": "Hi"}]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert isinstance(response_text, str)
    
    def test_send_messages_with_special_characters(self, llm_orchestrator):
        """
        Test with special characters in messages.
        
        Testing Concept: Test special character handling
        """
        messages = [
            {"role": "user", "content": "Test with émojis 🎉 and spëcial çhars"}
        ]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert isinstance(response_text, str)
    
    def test_send_messages_with_very_long_message(self, llm_orchestrator):
        """
        Test with very long message content.
        
        Testing Concept: Test large input
        """
        long_content = "A" * 10000
        messages = [{"role": "user", "content": long_content}]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert isinstance(response_text, str)
    
    def test_send_message_preserves_prompt_exactly(self, llm_orchestrator):
        """
        Test that prompt is passed to builder without modification.
        
        Testing Concept: Test data preservation
        """
        prompt = "Exact prompt with\nNewlines\tand\ttabs"
        
        llm_orchestrator.send_message(prompt)
        
        llm_orchestrator.prompt_builder.build_user_conversation_messages.assert_called_once_with(
            prompt
        )
    
    def test_send_messages_with_unicode_content(self, llm_orchestrator):
        """
        Test with unicode characters.
        
        Testing Concept: Test unicode handling
        """
        messages = [
            {"role": "user", "content": "你好世界 こんにちは مرحبا"}
        ]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert isinstance(response_text, str)
    
    @pytest.mark.asyncio
    async def test_send_message_stream_with_single_chunk(self, llm_orchestrator):
        """
        Test streaming with only one chunk.
        
        Testing Concept: Test single iteration
        """
        single_chunk = MagicMock()
        single_chunk.choices = [MagicMock()]
        single_chunk.choices[0].delta.content = "Single chunk"
        
        llm_orchestrator.client.chat.completions.create.return_value = iter([single_chunk])
        
        chunks = []
        async for chunk in llm_orchestrator.send_message_stream("Test"):
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert chunks[0] == "Single chunk"
    
    @pytest.mark.asyncio
    async def test_send_message_stream_with_many_chunks(self, llm_orchestrator):
        """
        Test streaming with many chunks.
        
        Testing Concept: Test many iterations
        """
        # Create 100 chunks
        many_chunks = []
        for i in range(100):
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = f"Chunk{i} "
            many_chunks.append(chunk)
        
        llm_orchestrator.client.chat.completions.create.return_value = iter(many_chunks)
        
        chunks = []
        async for chunk in llm_orchestrator.send_message_stream("Test"):
            chunks.append(chunk)
        
        assert len(chunks) == 100


# ============================================================================
# TEST CLASS: Configuration Variations
# ============================================================================


class TestConfigurationVariations:
    """Test different configuration scenarios."""
    
    def test_with_different_model_name(self, mock_env, mock_logger):
        """
        Test initialization with different model.
        
        Testing Concept: Test configuration variant
        """
        with patch("src.llm.llm_orchestrator.get_config_section") as mock_config:
            mock_config.return_value = {
                "model_name": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.5,
                "max_tokens": 2048,
            }
            
            with patch("src.llm.llm_orchestrator.OpenAI"):
                with patch("src.llm.llm_orchestrator.PromptBuilder"):
                    orchestrator = LLMOrchestrator()
                    
                    assert orchestrator.model_name == "gpt-4"
    
    def test_with_different_temperature(
        self, mock_env, mock_logger, mock_openai_client, mock_prompt_builder
    ):
        """
        Test API call with different temperature.
        
        Testing Concept: Test parameter variation
        """
        with patch("src.llm.llm_orchestrator.get_config_section") as mock_config:
            mock_config.return_value = {
                "model_name": "test-model",
                "base_url": "https://test.com",
                "temperature": 0.9,
                "max_tokens": 512,
            }
            
            with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
                mock_openai_class.return_value = mock_openai_client
                
                with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
                    mock_builder_class.return_value = mock_prompt_builder
                    
                    orchestrator = LLMOrchestrator()
                    orchestrator.client = mock_openai_client
                    
                    messages = [{"role": "user", "content": "Test"}]
                    orchestrator.send_messages(messages)
                    
                    # Verify temperature
                    call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
                    assert call_kwargs["temperature"] == 0.9
    
    def test_with_different_max_tokens(
        self, mock_env, mock_logger, mock_openai_client, mock_prompt_builder
    ):
        """
        Test API call with different max_tokens.
        
        Testing Concept: Test parameter variation
        """
        with patch("src.llm.llm_orchestrator.get_config_section") as mock_config:
            mock_config.return_value = {
                "model_name": "test-model",
                "base_url": "https://test.com",
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            
            with patch("src.llm.llm_orchestrator.OpenAI") as mock_openai_class:
                mock_openai_class.return_value = mock_openai_client
                
                with patch("src.llm.llm_orchestrator.PromptBuilder") as mock_builder_class:
                    mock_builder_class.return_value = mock_prompt_builder
                    
                    orchestrator = LLMOrchestrator()
                    orchestrator.client = mock_openai_client
                    
                    messages = [{"role": "user", "content": "Test"}]
                    orchestrator.send_messages(messages)
                    
                    # Verify max_tokens
                    call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
                    assert call_kwargs["max_tokens"] == 4096


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_conversation_flow(self, llm_orchestrator):
        """
        Test complete conversation flow.
        
        Testing Concept: Integration test
        """
        # 1. Send first message
        response1, _ = llm_orchestrator.send_message("What is AI?")
        assert isinstance(response1, str)
        
        # 2. Send follow-up with pre-built messages
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": response1},
            {"role": "user", "content": "Tell me more"}
        ]
        response2, _ = llm_orchestrator.send_messages(messages)
        assert isinstance(response2, str)
    
    @pytest.mark.asyncio
    async def test_streaming_full_response(self, llm_orchestrator, mock_stream_response):
        """
        Test streaming a complete response.
        
        Testing Concept: Integration test for streaming
        """
        llm_orchestrator.client.chat.completions.create.return_value = iter(mock_stream_response)
        
        full_response = ""
        async for chunk in llm_orchestrator.send_message_stream("Tell me a story"):
            full_response += chunk
        
        assert full_response == "Hello world!"


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("prompt", [
        "Simple question",
        "Question with\nnewlines",
        "Question with\ttabs",
        "Très long question " * 100,
        "",
        "?"
    ])
    def test_send_message_with_various_prompts(self, llm_orchestrator, prompt):
        """
        Test send_message with various prompt formats.
        
        Testing Concept: Parameterized input testing
        """
        response_text, _ = llm_orchestrator.send_message(prompt)
        
        assert isinstance(response_text, str)
    
    @pytest.mark.parametrize("role,content", [
        ("user", "Hello"),
        ("assistant", "Hi there"),
        ("system", "You are helpful"),
    ])
    def test_send_messages_with_various_roles(self, llm_orchestrator, role, content):
        """
        Test send_messages with different roles.
        
        Testing Concept: Parameterized role testing
        """
        messages = [{"role": role, "content": content}]
        
        response_text, _ = llm_orchestrator.send_messages(messages)
        
        assert isinstance(response_text, str)


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.llm.llm_orchestrator",
        "--cov-report=term-missing"
    ])

