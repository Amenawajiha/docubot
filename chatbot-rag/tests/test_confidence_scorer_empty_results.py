"""Test confidence scorer with empty retrieval results."""

import pytest

from src.confidence_scorer import ConfidenceScorer
from src.models import ConfidenceResult


def test_retrieval_confidence_with_empty_results():
    """Test that retrieval confidence returns 0.0 when no results are found."""
    scorer = ConfidenceScorer()
    
    # Test with empty list
    confidence = scorer._ConfidenceScorer__retrieval_confidence_score([])
    assert confidence == 0.0, f"Expected 0.0 for empty results, got {confidence}"


def test_overall_confidence_with_empty_retrieval_results():
    """Test that overall confidence calculation handles empty retrieval results."""
    scorer = ConfidenceScorer()
    
    # Mock LLM logprobs (neutral confidence) - should be list of floats
    llm_logprobs = [-0.693]  # exp(-0.693) ≈ 0.5
    
    result = scorer.run(retrieval_results=[], llm_logprobs=llm_logprobs)
    
    # Should be a valid ConfidenceResult
    assert isinstance(result, ConfidenceResult)
    assert result.retrieval_confidence == 0.0
    assert result.llm_confidence == pytest.approx(0.5, abs=0.1)  # exp(-0.693) ≈ 0.5
    # overall_confidence = retrieval_weight * retrieval_confidence + llm_weight * llm_confidence
    # With config weights (0.7, 0.3): 0.7 * 0.0 + 0.3 * 0.5 = 0.15
    assert result.overall_confidence == pytest.approx(0.15, abs=0.01)


if __name__ == "__main__":
    test_retrieval_confidence_with_empty_results()
    test_overall_confidence_with_empty_retrieval_results()
    print("All tests passed!")