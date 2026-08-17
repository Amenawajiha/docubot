"""
Orchestrates confidence scoring by combining results from LLM and retrieval-based scorers.

This class uses various confidence scoring mechanisms (e.g., LLM-based, retrieval-based)
and combines their results using predefined weights to provide an overall confidence score.
"""

import math
from typing import List, Optional

from src.models import ConfidenceResult, RetrievalResult, ScoringWeights
from src.utils.config_loader import get_config


class ConfidenceScorer:
    """
    Orchestrates confidence scoring by combining results from LLM and retrieval-based scorers.

    This class uses various confidence scoring mechanisms (e.g., LLM-based, retrieval-based)
    and combines their results using predefined weights to provide an overall confidence score.
    """

    def __init__(
        self,
    ):
        self.weights = ScoringWeights(
            retrieval_weight=get_config("confidence.retrieval_weight"),
            llm_weight=get_config("confidence.llm_weight"),
        )

    def __retrieval_confidence_score(
        self, retrieval_results: List[RetrievalResult]
    ) -> float:
        """Calculate retrieval confidence score."""
        # Handle case where no retrieval results are found
        if not retrieval_results:
            return 0.0
        
        min_relevance_threshold = get_config("confidence.min_relevance_threshold")
        avg_relevance = sum(
            result.relevance_score for result in retrieval_results
        ) / len(retrieval_results)
        coverage = any(
            result.relevance_score >= min_relevance_threshold
            for result in retrieval_results
        )
        return avg_relevance * coverage

    def run(
        self,
        retrieval_results: List[RetrievalResult],
        llm_logprobs: List[float] = None,
    ) -> ConfidenceResult:
        """
        Calculate overall confidence based on retrieval and LLM scores.

        Args:
            retrieval_results: Retrieved context chunks
            llm_logprobs: Log probabilities from LLM generation
        """
        retrieval_confidence = self.__retrieval_confidence_score(retrieval_results)
        llm_confidence = self.__llm_confidence_score(llm_logprobs)
        overall_confidence = (
            self.weights.retrieval_weight * retrieval_confidence
            + self.weights.llm_weight * llm_confidence
        )
        return ConfidenceResult(
            retrieval_confidence=retrieval_confidence,
            llm_confidence=llm_confidence,
            overall_confidence=overall_confidence,
            is_confident=overall_confidence >= 0.6,
            confidence_breakdown={
                "retrieval": retrieval_confidence,
                "llm": llm_confidence,
                "overall": overall_confidence,
            },
        )

    def __llm_confidence_score(self, logprobs: Optional[List[float]]) -> float:
        """
        Calculate confidence score from token logprobs.

        The confidence is derived from the average log probability of generated tokens.
        Higher (less negative) logprobs indicate higher model confidence.

        Args:
            logprobs: List of log probabilities for each generated token
                     (typically negative values, e.g., -0.5, -2.3)

        Returns:
            Confidence score between 0 and 1
            - 1.0 = very confident (logprobs close to 0)
            - 0.0 = not confident (very negative logprobs)

        Implementation:
            - If logprobs is None or empty, returns 0.5 (neutral confidence)
            - Calculates average logprob across all tokens
            - Converts to probability using exp(avg_logprob)
            - Clamps result to [0, 1] range
        """
        if not logprobs:
            return 0.5  # Neutral confidence when logprobs unavailable

        # Calculate average logprob
        avg_logprob = sum(logprobs) / len(logprobs)

        # Convert log probability to probability
        # logprob is typically negative (e.g., -0.5, -2.0)
        # exp(-0.5) ≈ 0.6, exp(-2.0) ≈ 0.14
        confidence = math.exp(avg_logprob)

        # Clamp to [0, 1] range (should already be in range, but safety check)
        return max(0.0, min(1.0, confidence))
