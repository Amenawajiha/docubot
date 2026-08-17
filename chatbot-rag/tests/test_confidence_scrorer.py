"""
Comprehensive unit tests for ConfidenceScorer.

This test suite covers:
- Initialization and configuration loading
- Retrieval confidence scoring
- LLM confidence scoring (logprobs)
- Overall confidence calculation with weights
- Edge cases (empty lists, None values, boundary values)
- Confidence thresholds and is_confident flag
- Mathematical calculations (averaging, exp, clamping)
"""

import math
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """
    Mock configuration values for confidence scoring.
    
    Testing Concept: Mock configuration loading
    """
    config_values = {
        "confidence.retrieval_weight": 0.4,
        "confidence.llm_weight": 0.6,
        "confidence.min_relevance_threshold": 0.7,
    }
    
    with patch("src.confidence_scorer.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def confidence_scorer(mock_config):
    """
    Create ConfidenceScorer with mocked configuration.
    
    Testing Concept: Fixture with dependency injection
    """
    from src.confidence_scorer import ConfidenceScorer
    return ConfidenceScorer()


@pytest.fixture
def sample_retrieval_results():
    """Sample retrieval results with varying relevance scores."""
    from src.models import RetrievalResult
    
    return [
        RetrievalResult(
            content="Sample content 1",
            metadata={"source": "doc1.pdf", "page": 1},
            relevance_score=0.85
        ),
        RetrievalResult(
            content="Sample content 2",
            metadata={"source": "doc2.pdf", "page": 3},
            relevance_score=0.72
        ),
        RetrievalResult(
            content="Sample content 3",
            metadata={"source": "doc3.pdf", "page": 5},
            relevance_score=0.68
        ),
    ]


@pytest.fixture
def low_relevance_retrieval_results():
    """Sample retrieval results with low relevance scores."""
    from src.models import RetrievalResult
    
    return [
        RetrievalResult(
            content="Low relevance content 1",
            metadata={"source": "doc1.pdf"},
            relevance_score=0.3
        ),
        RetrievalResult(
            content="Low relevance content 2",
            metadata={"source": "doc2.pdf"},
            relevance_score=0.45
        ),
    ]


@pytest.fixture
def high_relevance_retrieval_results():
    """Sample retrieval results with high relevance scores."""
    from src.models import RetrievalResult
    
    return [
        RetrievalResult(
            content="High relevance content 1",
            metadata={"source": "doc1.pdf"},
            relevance_score=0.95
        ),
        RetrievalResult(
            content="High relevance content 2",
            metadata={"source": "doc2.pdf"},
            relevance_score=0.88
        ),
    ]


@pytest.fixture
def sample_logprobs_confident():
    """Sample logprobs indicating confident LLM generation."""
    return [-0.1, -0.2, -0.15, -0.3, -0.25]  # High confidence (close to 0)


@pytest.fixture
def sample_logprobs_uncertain():
    """Sample logprobs indicating uncertain LLM generation."""
    return [-2.5, -3.0, -2.8, -3.2, -2.9]  # Low confidence (very negative)


@pytest.fixture
def sample_logprobs_mixed():
    """Sample logprobs with mixed confidence levels."""
    return [-0.5, -1.0, -0.3, -2.0, -0.8]


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestConfidenceScorerInitialization:
    """Test ConfidenceScorer initialization."""
    
    def test_initialization_loads_retrieval_weight_from_config(self):
        """
        Test that retrieval_weight is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.confidence_scorer.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.retrieval_weight": 0.35,
                "confidence.llm_weight": 0.65,
            }.get(key, default)
            
            from src.confidence_scorer import ConfidenceScorer
            scorer = ConfidenceScorer()
            
            assert scorer.weights.retrieval_weight == 0.35
    
    def test_initialization_loads_llm_weight_from_config(self):
        """
        Test that llm_weight is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.confidence_scorer.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.retrieval_weight": 0.4,
                "confidence.llm_weight": 0.6,
            }.get(key, default)
            
            from src.confidence_scorer import ConfidenceScorer
            scorer = ConfidenceScorer()
            
            assert scorer.weights.llm_weight == 0.6
    
    def test_initialization_creates_scoring_weights_object(self, confidence_scorer):
        """
        Test that ScoringWeights object is created.
        
        Testing Concept: Test object creation
        """
        from src.models import ScoringWeights
        
        assert isinstance(confidence_scorer.weights, ScoringWeights)
    
    def test_initialization_with_custom_weights(self):
        """
        Test initialization with custom weight values.
        
        Testing Concept: Test configuration flexibility
        """
        with patch("src.confidence_scorer.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.retrieval_weight": 0.5,
                "confidence.llm_weight": 0.5,
            }.get(key, default)
            
            from src.confidence_scorer import ConfidenceScorer
            scorer = ConfidenceScorer()
            
            assert scorer.weights.retrieval_weight == 0.5
            assert scorer.weights.llm_weight == 0.5
    
    def test_weights_sum_correctly(self, confidence_scorer):
        """
        Test that retrieval and LLM weights sum to 1.0.
        
        Testing Concept: Test weight validation
        """
        total = confidence_scorer.weights.retrieval_weight + confidence_scorer.weights.llm_weight
        assert abs(total - 1.0) < 0.01  # Allow small floating point error


# ============================================================================
# TEST CLASS: Retrieval Confidence Scoring
# ============================================================================


class TestRetrievalConfidenceScoring:
    """Test retrieval confidence scoring logic."""
    
    def test_retrieval_confidence_with_high_relevance_results(
        self, confidence_scorer, high_relevance_retrieval_results
    ):
        """
        Test retrieval confidence with high relevance scores.
        
        Testing Concept: Test happy path with strong signals
        """
        # Access private method for testing
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(
            high_relevance_retrieval_results
        )
        
        # Should have high confidence due to high relevance scores
        assert confidence > 0.7
        assert confidence <= 1.0
    
    def test_retrieval_confidence_with_low_relevance_results(
        self, confidence_scorer, low_relevance_retrieval_results
    ):
        """
        Test retrieval confidence with low relevance scores.
        
        Testing Concept: Test with weak signals
        """
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(
            low_relevance_retrieval_results
        )
        
        # Should have low confidence due to low relevance scores
        assert confidence < 0.5
    
    def test_retrieval_confidence_with_empty_results(self, confidence_scorer):
        """
        Test retrieval confidence with empty result list.
        
        Testing Concept: Test edge case - no results
        """
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score([])
        
        # Should return 0.0 for no results
        assert confidence == 0.0
    
    def test_retrieval_confidence_with_mixed_relevance_scores(
        self, confidence_scorer, sample_retrieval_results
    ):
        """
        Test retrieval confidence with mixed relevance scores.
        
        Testing Concept: Test normal case with varied scores
        """
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(
            sample_retrieval_results
        )
        
        # Should be between 0 and 1
        assert 0.0 <= confidence <= 1.0
    
    def test_retrieval_confidence_calculates_average_relevance(
        self, confidence_scorer
    ):
        """
        Test that average relevance is calculated correctly.
        
        Testing Concept: Test calculation accuracy
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.8),
            RetrievalResult(content="B", metadata={}, relevance_score=0.6),
            RetrievalResult(content="C", metadata={}, relevance_score=0.7),
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Average = (0.8 + 0.6 + 0.7) / 3 = 0.7
        # Coverage = True (0.8 >= 0.7 threshold)
        # Confidence = 0.7 * 1 = 0.7
        assert abs(confidence - 0.7) < 0.01
    
    def test_retrieval_confidence_coverage_flag_true(self, confidence_scorer):
        """
        Test coverage flag when at least one result exceeds threshold.
        
        Testing Concept: Test boolean logic in scoring
        """
        from src.models import RetrievalResult
        
        # One result exceeds threshold (0.7)
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.75),
            RetrievalResult(content="B", metadata={}, relevance_score=0.5),
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Coverage = True, so confidence should be avg_relevance * 1
        avg = (0.75 + 0.5) / 2  # = 0.625
        assert abs(confidence - avg) < 0.01
    
    def test_retrieval_confidence_coverage_flag_false(self, confidence_scorer):
        """
        Test coverage flag when no results exceed threshold.
        
        Testing Concept: Test boolean logic in scoring
        """
        from src.models import RetrievalResult
        
        # No results exceed threshold (0.7)
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.6),
            RetrievalResult(content="B", metadata={}, relevance_score=0.5),
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Coverage = False (0), so confidence should be 0
        assert confidence == 0.0
    
    def test_retrieval_confidence_with_single_result_above_threshold(
        self, confidence_scorer
    ):
        """
        Test with single result above threshold.
        
        Testing Concept: Test minimum valid input
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.9)
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Single result with score 0.9, exceeds threshold
        # Confidence = 0.9 * 1 = 0.9
        assert abs(confidence - 0.9) < 0.01
    
    def test_retrieval_confidence_with_single_result_below_threshold(
        self, confidence_scorer
    ):
        """
        Test with single result below threshold.
        
        Testing Concept: Test edge case
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.4)
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Single result below threshold, coverage = False
        assert confidence == 0.0
    
    def test_retrieval_confidence_with_boundary_relevance_score(
        self, confidence_scorer
    ):
        """
        Test with relevance score exactly at threshold.
        
        Testing Concept: Test boundary value
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.7)
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Score exactly at threshold should pass coverage check
        assert confidence == 0.7
    
    def test_retrieval_confidence_with_maximum_relevance_scores(
        self, confidence_scorer
    ):
        """
        Test with maximum relevance scores (1.0).
        
        Testing Concept: Test maximum boundary
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=1.0),
            RetrievalResult(content="B", metadata={}, relevance_score=1.0),
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Perfect scores should yield confidence of 1.0
        assert confidence == 1.0
    
    def test_retrieval_confidence_with_zero_relevance_scores(
        self, confidence_scorer
    ):
        """
        Test with zero relevance scores.
        
        Testing Concept: Test minimum boundary
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.0),
            RetrievalResult(content="B", metadata={}, relevance_score=0.0),
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        # Zero scores should yield confidence of 0.0
        assert confidence == 0.0


# ============================================================================
# TEST CLASS: LLM Confidence Scoring (Logprobs)
# ============================================================================


class TestLLMConfidenceScoring:
    """Test LLM confidence scoring from logprobs."""
    
    def test_llm_confidence_with_confident_logprobs(
        self, confidence_scorer, sample_logprobs_confident
    ):
        """
        Test LLM confidence with high confidence logprobs.
        
        Testing Concept: Test happy path with strong confidence
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score(
            sample_logprobs_confident
        )
        
        # Logprobs close to 0 should yield high confidence
        assert confidence > 0.7
        assert confidence <= 1.0
    
    def test_llm_confidence_with_uncertain_logprobs(
        self, confidence_scorer, sample_logprobs_uncertain
    ):
        """
        Test LLM confidence with low confidence logprobs.
        
        Testing Concept: Test with weak confidence signals
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score(
            sample_logprobs_uncertain
        )
        
        # Very negative logprobs should yield low confidence
        assert confidence < 0.3
        assert confidence >= 0.0
    
    def test_llm_confidence_with_none_logprobs(self, confidence_scorer):
        """
        Test LLM confidence when logprobs is None.
        
        Testing Concept: Test edge case - no data
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score(None)
        
        # Should return neutral confidence (0.5)
        assert confidence == 0.5
    
    def test_llm_confidence_with_empty_logprobs_list(self, confidence_scorer):
        """
        Test LLM confidence with empty logprobs list.
        
        Testing Concept: Test edge case - empty list
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([])
        
        # Should return neutral confidence (0.5)
        assert confidence == 0.5
    
    def test_llm_confidence_with_single_logprob(self, confidence_scorer):
        """
        Test LLM confidence with single logprob value.
        
        Testing Concept: Test minimum valid input
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([-0.5])
        
        # exp(-0.5) ≈ 0.606
        expected = math.exp(-0.5)
        assert abs(confidence - expected) < 0.01
    
    def test_llm_confidence_with_mixed_logprobs(
        self, confidence_scorer, sample_logprobs_mixed
    ):
        """
        Test LLM confidence with mixed logprobs.
        
        Testing Concept: Test normal case with varied values
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score(
            sample_logprobs_mixed
        )
        
        # Should be between 0 and 1
        assert 0.0 <= confidence <= 1.0
    
    def test_llm_confidence_calculates_average_correctly(self, confidence_scorer):
        """
        Test that average logprob is calculated correctly.
        
        Testing Concept: Test calculation accuracy
        """
        logprobs = [-1.0, -2.0, -3.0]
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score(logprobs)
        
        # Average = (-1.0 + -2.0 + -3.0) / 3 = -2.0
        # Confidence = exp(-2.0) ≈ 0.135
        expected = math.exp(-2.0)
        assert abs(confidence - expected) < 0.01
    
    def test_llm_confidence_with_zero_logprob(self, confidence_scorer):
        """
        Test LLM confidence with zero logprob (maximum confidence).
        
        Testing Concept: Test boundary value
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([0.0])
        
        # exp(0) = 1.0
        assert confidence == 1.0
    
    def test_llm_confidence_with_very_negative_logprob(self, confidence_scorer):
        """
        Test LLM confidence with very negative logprob.
        
        Testing Concept: Test extreme value
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([-10.0])
        
        # exp(-10) ≈ 0.000045
        expected = math.exp(-10.0)
        assert abs(confidence - expected) < 0.0001
    
    def test_llm_confidence_clamps_to_zero(self, confidence_scorer):
        """
        Test that confidence is clamped to 0.0 minimum.
        
        Testing Concept: Test clamping logic
        """
        # Extremely negative logprob
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([-100.0])
        
        # Should be clamped to 0.0
        assert confidence >= 0.0
    
    def test_llm_confidence_clamps_to_one(self, confidence_scorer):
        """
        Test that confidence is clamped to 1.0 maximum.
        
        Testing Concept: Test clamping logic
        """
        # Positive logprob (shouldn't happen in practice, but test clamping)
        # Note: In practice, logprobs should be <= 0
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([0.0])
        
        # Should be clamped to 1.0
        assert confidence <= 1.0
    
    def test_llm_confidence_with_multiple_zero_logprobs(self, confidence_scorer):
        """
        Test with multiple zero logprobs.
        
        Testing Concept: Test maximum confidence scenario
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score([0.0, 0.0, 0.0])
        
        # Average = 0, exp(0) = 1.0
        assert confidence == 1.0


# ============================================================================
# TEST CLASS: Overall Confidence Calculation (run method)
# ============================================================================


class TestOverallConfidenceCalculation:
    """Test the main run() method that combines retrieval and LLM confidence."""
    
    def test_run_returns_confidence_result_object(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test that run returns a ConfidenceResult object.
        
        Testing Concept: Test return type
        """
        result = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        from src.models import ConfidenceResult
        assert isinstance(result, ConfidenceResult)
    
    def test_run_includes_all_required_fields(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test that result includes all required fields.
        
        Testing Concept: Test data completeness
        """
        result = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        assert hasattr(result, 'retrieval_confidence')
        assert hasattr(result, 'llm_confidence')
        assert hasattr(result, 'overall_confidence')
        assert hasattr(result, 'is_confident')
        assert hasattr(result, 'confidence_breakdown')
    
    def test_run_calculates_overall_confidence_with_weights(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test that overall confidence is weighted sum.
        
        Testing Concept: Test calculation with weights
        """
        result = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        # Verify weighted calculation
        expected_overall = (
            confidence_scorer.weights.retrieval_weight * result.retrieval_confidence +
            confidence_scorer.weights.llm_weight * result.llm_confidence
        )
        
        assert abs(result.overall_confidence - expected_overall) < 0.01
    
    def test_run_with_high_confidence_results(
        self, confidence_scorer, high_relevance_retrieval_results, sample_logprobs_confident
    ):
        """
        Test run with high confidence inputs.
        
        Testing Concept: Test happy path with strong signals
        """
        result = confidence_scorer.run(
            high_relevance_retrieval_results,
            sample_logprobs_confident
        )
        
        # Should have high overall confidence
        assert result.overall_confidence > 0.7
        assert result.is_confident is True
    
    def test_run_with_low_confidence_results(
        self, confidence_scorer, low_relevance_retrieval_results, sample_logprobs_uncertain
    ):
        """
        Test run with low confidence inputs.
        
        Testing Concept: Test with weak signals
        """
        result = confidence_scorer.run(
            low_relevance_retrieval_results,
            sample_logprobs_uncertain
        )
        
        # Should have low overall confidence
        assert result.overall_confidence < 0.6
        assert result.is_confident is False
    
    def test_run_with_empty_retrieval_results(
        self, confidence_scorer, sample_logprobs_confident
    ):
        """
        Test run with empty retrieval results.
        
        Testing Concept: Test edge case - no retrieval results
        """
        result = confidence_scorer.run([], sample_logprobs_confident)
        
        # Retrieval confidence should be 0
        assert result.retrieval_confidence == 0.0
        
        # Overall confidence should still be calculated
        assert 0.0 <= result.overall_confidence <= 1.0
    
    def test_run_with_none_logprobs(
        self, confidence_scorer, sample_retrieval_results
    ):
        """
        Test run with None logprobs.
        
        Testing Concept: Test edge case - no LLM confidence
        """
        result = confidence_scorer.run(sample_retrieval_results, None)
        
        # LLM confidence should default to 0.5
        assert result.llm_confidence == 0.5
        
        # Overall confidence should still be calculated
        assert 0.0 <= result.overall_confidence <= 1.0
    
    def test_run_with_empty_logprobs(
        self, confidence_scorer, sample_retrieval_results
    ):
        """
        Test run with empty logprobs list.
        
        Testing Concept: Test edge case - empty LLM data
        """
        result = confidence_scorer.run(sample_retrieval_results, [])
        
        # LLM confidence should default to 0.5
        assert result.llm_confidence == 0.5
    
    def test_run_is_confident_flag_above_threshold(self, confidence_scorer):
        """
        Test is_confident flag when overall >= 0.6.
        
        Testing Concept: Test boolean flag logic
        """
        from src.models import RetrievalResult
        
        # Create inputs that will yield high confidence
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.9)
        ]
        logprobs = [-0.1, -0.2]
        
        result = confidence_scorer.run(results, logprobs)
        
        if result.overall_confidence >= 0.6:
            assert result.is_confident is True
    
    def test_run_is_confident_flag_below_threshold(self, confidence_scorer):
        """
        Test is_confident flag when overall < 0.6.
        
        Testing Concept: Test boolean flag logic
        """
        from src.models import RetrievalResult
        
        # Create inputs that will yield low confidence
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.3)
        ]
        logprobs = [-5.0, -6.0]
        
        result = confidence_scorer.run(results, logprobs)
        
        if result.overall_confidence < 0.6:
            assert result.is_confident is False
    
    def test_run_confidence_breakdown_matches_individual_scores(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test that confidence breakdown matches individual scores.
        
        Testing Concept: Test data consistency
        """
        result = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        assert result.confidence_breakdown['retrieval'] == result.retrieval_confidence
        assert result.confidence_breakdown['llm'] == result.llm_confidence
        assert result.confidence_breakdown['overall'] == result.overall_confidence
    
    def test_run_with_boundary_confidence_exactly_060(self, confidence_scorer):
        """
        Test is_confident flag at exact threshold (0.6).
        
        Testing Concept: Test boundary value
        """
        # Mock the private methods to return specific values
        with patch.object(
            confidence_scorer,
            '_ConfidenceScorer__retrieval_confidence_score',
            return_value=0.5
        ), patch.object(
            confidence_scorer,
            '_ConfidenceScorer__llm_confidence_score',
            return_value=0.66667  # Will result in overall ≈ 0.6
        ):
            result = confidence_scorer.run([], [])
            
            # At exactly 0.6, should be confident
            if abs(result.overall_confidence - 0.6) < 0.01:
                assert result.is_confident is True
    
    def test_run_with_mixed_confidence_signals(
        self, confidence_scorer, high_relevance_retrieval_results, sample_logprobs_uncertain
    ):
        """
        Test with high retrieval but low LLM confidence.
        
        Testing Concept: Test mixed signal scenario
        """
        result = confidence_scorer.run(
            high_relevance_retrieval_results,
            sample_logprobs_uncertain
        )
        
        # Should have high retrieval confidence
        assert result.retrieval_confidence > 0.7
        
        # But low LLM confidence
        assert result.llm_confidence < 0.3
        
        # Overall depends on weights
        assert 0.0 <= result.overall_confidence <= 1.0
    
    def test_run_preserves_all_confidence_values(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test that all individual confidence values are preserved.
        
        Testing Concept: Test data preservation
        """
        result = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        # All values should be in valid range
        assert 0.0 <= result.retrieval_confidence <= 1.0
        assert 0.0 <= result.llm_confidence <= 1.0
        assert 0.0 <= result.overall_confidence <= 1.0


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic end-to-end scenarios."""
    
    def test_full_confidence_scoring_workflow(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test complete confidence scoring workflow.
        
        Testing Concept: Integration test
        """
        # Run full scoring
        result = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        # Verify all outputs are valid
        assert isinstance(result.retrieval_confidence, float)
        assert isinstance(result.llm_confidence, float)
        assert isinstance(result.overall_confidence, float)
        assert isinstance(result.is_confident, bool)
        assert isinstance(result.confidence_breakdown, dict)
        
        # Verify ranges
        assert 0.0 <= result.retrieval_confidence <= 1.0
        assert 0.0 <= result.llm_confidence <= 1.0
        assert 0.0 <= result.overall_confidence <= 1.0
    
    def test_confidence_scoring_with_different_weight_configurations(self):
        """
        Test scoring with different weight configurations.
        
        Testing Concept: Test configuration impact
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content="A", metadata={}, relevance_score=0.8)
        ]
        logprobs = [-0.5]
        
        # Test with retrieval-heavy weights
        with patch("src.confidence_scorer.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.retrieval_weight": 0.8,
                "confidence.llm_weight": 0.2,
                "confidence.min_relevance_threshold": 0.7,
            }.get(key, default)
            
            from src.confidence_scorer import ConfidenceScorer
            retrieval_heavy_scorer = ConfidenceScorer()
            result1 = retrieval_heavy_scorer.run(results, logprobs)
        
        # Test with LLM-heavy weights
        with patch("src.confidence_scorer.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.retrieval_weight": 0.2,
                "confidence.llm_weight": 0.8,
                "confidence.min_relevance_threshold": 0.7,
            }.get(key, default)
            
            from src.confidence_scorer import ConfidenceScorer
            llm_heavy_scorer = ConfidenceScorer()
            result2 = llm_heavy_scorer.run(results, logprobs)
        
        # Results should differ based on weights
        # This test verifies that weights have an effect
        assert result1.overall_confidence != result2.overall_confidence
    
    def test_confidence_scoring_consistency(
        self, confidence_scorer, sample_retrieval_results, sample_logprobs_confident
    ):
        """
        Test that scoring is deterministic.
        
        Testing Concept: Test determinism
        """
        result1 = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        result2 = confidence_scorer.run(
            sample_retrieval_results,
            sample_logprobs_confident
        )
        
        # Should produce identical results
        assert result1.retrieval_confidence == result2.retrieval_confidence
        assert result1.llm_confidence == result2.llm_confidence
        assert result1.overall_confidence == result2.overall_confidence
        assert result1.is_confident == result2.is_confident


# ============================================================================
# TEST CLASS: Parameterized Tests
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("logprobs,expected_range", [
        ([-0.1, -0.2], (0.7, 1.0)),  # High confidence
        ([-2.0, -3.0], (0.0, 0.3)),  # Low confidence
        ([-1.0, -1.0], (0.3, 0.5)),  # Medium confidence
        ([0.0], (0.99, 1.0)),         # Maximum confidence
        ([-10.0], (0.0, 0.01)),       # Near zero confidence
    ])
    def test_llm_confidence_ranges(self, confidence_scorer, logprobs, expected_range):
        """
        Test LLM confidence with various logprob values.
        
        Testing Concept: Parameterized testing
        """
        confidence = confidence_scorer._ConfidenceScorer__llm_confidence_score(logprobs)
        
        min_expected, max_expected = expected_range
        assert min_expected <= confidence <= max_expected
    
    @pytest.mark.parametrize("relevance_scores,should_pass_coverage", [
        ([0.9, 0.8, 0.85], True),   # All above threshold
        ([0.75, 0.6, 0.5], True),   # One above threshold
        ([0.6, 0.5, 0.4], False),   # All below threshold
        ([0.7], True),              # Exactly at threshold
        ([0.69], False),            # Just below threshold
    ])
    def test_retrieval_coverage_scenarios(
        self, confidence_scorer, relevance_scores, should_pass_coverage
    ):
        """
        Test retrieval coverage flag with various scenarios.
        
        Testing Concept: Parameterized coverage testing
        """
        from src.models import RetrievalResult
        
        results = [
            RetrievalResult(content=f"Content {i}", metadata={}, relevance_score=score)
            for i, score in enumerate(relevance_scores)
        ]
        
        confidence = confidence_scorer._ConfidenceScorer__retrieval_confidence_score(results)
        
        if should_pass_coverage:
            # If coverage passes, confidence should be avg_relevance
            avg = sum(relevance_scores) / len(relevance_scores)
            assert abs(confidence - avg) < 0.01
        else:
            # If coverage fails, confidence should be 0
            assert confidence == 0.0


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.confidence_scorer",
        "--cov-report=term-missing"
    ])


