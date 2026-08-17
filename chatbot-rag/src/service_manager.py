"""Singleton service manager for heavy components.

This module provides a singleton pattern for managing expensive-to-initialize
components like VectorRetriever and LLMOrchestrator. Components are initialized
once at application startup and reused across all requests.
"""

from typing import Optional

from .vector.vector_retriever import VectorRetriever
from .llm.llm_orchestrator import LLMOrchestrator
from .llm.prompt_builder import PromptBuilder
from .confidence_scorer import ConfidenceScorer
from .llm.clarification_manager import ClarificationManager
from .utils.log_helper import logger
from .ingestion.embedding_manager import EmbeddingManager


class ServiceManager:
    """Singleton manager for shared services."""

    _instance: Optional["ServiceManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize services only once."""
        if not ServiceManager._initialized:
            logger.info("Initializing shared services...")

            # Initialize EmbeddingManager first (needed by VectorRetriever)
            self.embedding_manager = EmbeddingManager()

            # Initialize VectorRetriever with shared embedding_manager
            self.vector_retriever = VectorRetriever(
                embedding_manager=self.embedding_manager
            )

            # Initialize LLM orchestrator
            self.llm_orchestrator = LLMOrchestrator()

            # Initialize lightweight components
            self.confidence_scorer = ConfidenceScorer()
            self.prompt_builder = PromptBuilder()
            self.clarification_manager = ClarificationManager()

            ServiceManager._initialized = True
            logger.info("Shared services initialized successfully")

    def get_vector_retriever(self) -> VectorRetriever:
        """Get the shared VectorRetriever instance."""
        return self.vector_retriever

    def get_llm_orchestrator(self) -> LLMOrchestrator:
        """Get the shared LLMOrchestrator instance."""
        return self.llm_orchestrator

    def get_confidence_scorer(self) -> ConfidenceScorer:
        """Get the shared ConfidenceScorer instance."""
        return self.confidence_scorer

    def get_prompt_builder(self) -> PromptBuilder:
        """Get the shared PromptBuilder instance."""
        return self.prompt_builder

    def get_clarification_manager(self) -> ClarificationManager:
        """Get the shared ClarificationManager instance."""
        return self.clarification_manager


# Global instance
_service_manager: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """Get or create the global ServiceManager instance."""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager