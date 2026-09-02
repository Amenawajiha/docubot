"""Clarification manager for handling low-confidence queries."""

from typing import Dict, List

from src.llm.llm_orchestrator import LLMOrchestrator
from src.llm.prompt_builder import PromptBuilder
from src.models import ConfidenceResult, RetrievalResult
from src.utils.config_loader import get_config
from src.utils import logger


class ClarificationManager:
    """Manages clarifying questions when confidence is low."""

    def __init__(self):
        """
        Initialize clarification manager.
        """
        self.llm_orchestrator = LLMOrchestrator()
        self.confidence_threshold = get_config("confidence.threshold")
        self.max_attempts = get_config("clarification.max_attempts")
        self.__attempt_count = 0

    def should_clarify(
        self, confidence_result: ConfidenceResult, conversation_history: List = None
    ) -> bool:
        """
        Check if clarification is needed.

        Args:
            confidence_result: Confidence result from scorer
            conversation_history: Recent conversation history to check for previous clarifications

        Returns:
            True if clarification is needed, False otherwise
        """
        # Check if the last assistant message was a clarification
        # If so, don't ask another clarification immediately (user just responded)
        for msg in reversed(conversation_history or []):
            if msg.get("role") == "assistant":
                # Check if this was a clarification question
                content = msg.get("content", "").lower()
                metadata = msg.get("metadata", {})
                # Detect clarification by metadata or question patterns
                if metadata.get("type") == "clarification":
                    # Last assistant message was clarification; user just responded
                    # Don't ask another clarification; let it fall through to answer/fallback
                    logger.debug(
                        "Clarification skipped: last assistant message was a clarification"
                    )
                    return False
                break  # Only check the most recent assistant message

        # Clarify if confidence is low AND haven't exceeded max attempts
        return (
            confidence_result.overall_confidence < self.confidence_threshold
            and self.__attempt_count < self.max_attempts
        )

    def generate_clarifying_question(
        self,
        query: str,
        context: List[RetrievalResult],
        confidence_result: ConfidenceResult,
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        """
        Generate a clarifying question using LLM.

        Args:
            query: Original user query
            context: Retrieved context
            confidence_result: Confidence result with breakdown

        Returns:
            Clarifying question to ask the user
        """
        # Build clarification messages with proper role separation
        messages = PromptBuilder().build_clarification_messages(
            query=query,
            context=context,
            retrieval_confidence=confidence_result.retrieval_confidence,
            llm_confidence=confidence_result.llm_confidence,
            overall_confidence=confidence_result.overall_confidence,
            conversation_history=conversation_history,
        )

        # Use LLM to generate clarifying question
        logger.debug('Context for clarification LLM: %s', context)
        res = self.llm_orchestrator.send_messages(messages)
        clarifying_question = res[0] if isinstance(res, (tuple, list)) else res
        self.__attempt_count += 1
        return clarifying_question.strip()

    def reset_attempts(self):
        """
        Reset the attempt count.
        """
        self.__attempt_count = 0

class TenantClarificationManager:
    """Per-tenant clarification manager with isolated attempt tracking.
    
    Unlike the shared ClarificationManager which creates its own LLMOrchestrator,
    this version accepts a tenant-specific one. Each tenant also has its own
    attempt counter, preventing cross-tenant interference.
    """
    
    def __init__(self, llm_orchestrator, prompt_builder):
        self.llm_orchestrator = llm_orchestrator
        self.prompt_builder = prompt_builder  # TenantPromptBuilder instance
        self.confidence_threshold = get_config("confidence.threshold", default=0.5)
        self.max_attempts = get_config("clarification.max_attempts")
        self.__attempt_count = 0  # Per-instance, so per-tenant
    
    def should_clarify(self, confidence_result: ConfidenceResult, conversation_history: List = None) -> bool:
        """Check if clarification is needed using tenant threshold."""
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant":
                    metadata = msg.get("metadata", {})
                    if metadata.get("type") == "clarification":
                        logger.debug("Clarification skipped: last assistant message was a clarification")
                        return False
                    break
        
        return (
            confidence_result.overall_confidence < self.confidence_threshold
            and self.__attempt_count < self.max_attempts
        )
    
    def generate_clarifying_question(
        self,
        query: str,
        context: List,
        confidence_result: ConfidenceResult,
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        messages = self.prompt_builder.build_clarification_messages(
            query=query,
            context=context,
            retrieval_confidence=confidence_result.retrieval_confidence,
            llm_confidence=confidence_result.llm_confidence,
            overall_confidence=confidence_result.overall_confidence,
            conversation_history=conversation_history,
        )
        res = self.llm_orchestrator.send_messages(messages)
        clarifying_question = res[0] if isinstance(res, (tuple, list)) else res
        self.__attempt_count += 1
        return clarifying_question.strip()
    
    def reset_attempts(self):
        self.__attempt_count = 0
