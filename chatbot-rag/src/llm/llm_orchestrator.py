"""LLM orchestrator for managing language model inference."""

import os
from typing import AsyncIterator, List, Optional, Tuple, Any

from dotenv import load_dotenv
from openai import OpenAI

from src.llm.prompt_builder import PromptBuilder
from src.models import RetrievalResult
from src.utils import logger
from src.utils.config_loader import get_config_section, get_config
from src.utils.exceptions import LLMException

load_dotenv()


class LLMOrchestrator:
    """Orchestrator for LLM inference operations using Groq API."""

    def __init__(self):
        """
        Initialize the LLM orchestrator.

        Args:
            model_name: Name of the LLM model
            base_url: Groq API base URL
        """
        self.__config = get_config_section("llm")

        self.model_name = self.__config.get("model_name")

        self.client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url=self.__config.get("base_url"),
        )

        self.prompt_builder = PromptBuilder()

    def send_message(self, prompt: str) -> Tuple[str, Optional[List[float]]]:
        """
        Send message to LLM and get response with logprobs.

        System instructions are set once per session.
        Only the user message changes per query.

        Args:
            prompt: User query with context

        Returns:
            Tuple of (response_text, logprobs_list)
            logprobs_list contains the logprob for each token, or None if disabled

        Raises:
            LLMException: If API call fails
        """
        messages = self.prompt_builder.build_user_conversation_messages(prompt)
        
        return self.send_messages(messages)

    def send_messages(self, messages: list) -> Tuple[str, Optional[List[float]]]:
        """
        Send pre-built messages to LLM and get response with logprobs.

        Use this when you have already constructed the complete message array
        (e.g., for specialized prompts like clarification).

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            Tuple of (response_text, logprobs_list, usage)
            logprobs_list contains the logprob for each token, or None if disabled

        Raises:
            LLMException: If API call fails
        """
        enable_logprobs = self.__config.get("enable_logprobs", False)
        try:
            # Build API call parameters
            api_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.__config.get("temperature"),
                "max_tokens": self.__config.get("max_tokens"),
            }

            # Add logprobs if enabled
            if enable_logprobs:
                api_params["logprobs"] = True
                api_params["top_logprobs"] = self.__config.get("logprobs_top_k", 5)

            response = self.client.chat.completions.create(**api_params)

            # Extract response text
            response_text = response.choices[0].message.content

            # Extract logprobs if available
            logprobs_list = None
            if enable_logprobs and response.choices[0].logprobs:
                # Extract the logprob value for each token
                logprobs_list = [
                    token_data.logprob
                    for token_data in response.choices[0].logprobs.content
                ]

            logger.debug("LLM RESPONSE: %s", response_text)

            usage = getattr(response, "usage", None)
            return response_text, logprobs_list, usage

        except Exception as e:
            raise LLMException(f"AI API call failed: {str(e)}") from e

    async def send_message_stream(self, prompt: str) -> AsyncIterator[str]:
        """
        Send message to LLM and stream response.

        System instructions are set once per session.
        Only the user message changes per query.

        Args:
            prompt: User query with context

        Yields:
            Response text chunks

        Raises:
            LLMException: If API call fails
        """
        try:
            messages = self.prompt_builder.build_user_conversation_messages(prompt)

            logger.debug("DEBUG LLM STREAM INPUT MESSAGES: %s", messages)

            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.__config.get("temperature"),
                max_tokens=self.__config.get("max_tokens"),
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    # Debug each streamed chunk
                    logger.debug(
                        "DEBUG LLM STREAM CHUNK: %s", chunk.choices[0].delta.content
                    )
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise LLMException(f"AI API streaming failed: {str(e)}") from e

class TenantLLMOrchestrator:
    """LLM orchestrator configured per-tenant from ChatbotConfig.
    
    Supports Groq and OpenAI providers. Anthropic is deferred due to
    SDK incompatibility (requires litellm or conditional client).
    """
    
    PROVIDER_URLS = {
        "groq": "https://api.groq.com/openai/v1",
        "openai": "https://api.openai.com/v1",
    }
    
    def __init__(self, config: "ChatbotConfig"):
        self.model_name = config.llm_model
        
        # Source hyperparameters from global config.yaml per design decision
        self.temperature = get_config("llm.temperature", default=0.3)
        self.max_tokens = get_config("llm.max_tokens", default=1024)
        self.enable_logprobs = get_config("llm.enable_logprobs", default=False)
        self.logprobs_top_k = get_config("llm.logprobs_top_k", default=5)
        
        base_url = self.PROVIDER_URLS.get(config.llm_provider)
        if not base_url:
            raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
        
        api_key = config.llm_api_key or os.environ.get(f"{config.llm_provider.upper()}_API_KEY")
        if not api_key:
            raise ValueError(
                f"No API key available for provider {config.llm_provider}. "
                f"Provide via chatbot_config or {config.llm_provider.upper()}_API_KEY env var."
            )
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def send_messages(self, messages: list) -> Tuple[str, Optional[List[float]], Any]:
        """
        Send pre-built messages to LLM and get response with logprobs.
        """
        try:
            # Build API call parameters
            api_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if self.enable_logprobs:
                api_params["logprobs"] = True
                api_params["top_logprobs"] = self.logprobs_top_k

            response = self.client.chat.completions.create(**api_params)
            response_text = response.choices[0].message.content
            
            logprobs_list = None
            if self.enable_logprobs and response.choices[0].logprobs:
                # Extract the logprob value for each token
                logprobs_list = [
                    token_data.logprob
                    for token_data in response.choices[0].logprobs.content
                ]
            
            logger.debug("LLM RESPONSE (Tenant): %s", response_text)
            
            usage = getattr(response, "usage", None)
            return response_text, logprobs_list, usage

        except Exception as e:
            raise LLMException(f"AI API call failed: {str(e)}") from e
