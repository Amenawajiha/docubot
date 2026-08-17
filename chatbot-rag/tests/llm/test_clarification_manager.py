"""
Comprehensive unit tests for ClarificationManager.

This test suite covers:
- Initialization and configuration
- Clarification decision logic (should_clarify)
- Clarifying question generation
- Attempt tracking and limits
- Conversation history analysis
- Edge cases and error handling
"""

import os
import sys
from unittest.mock import MagicMock, patch, call

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.llm.clarification_manager import ClarificationManager
from src.models import ConfidenceResult, RetrievalResult


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
        "confidence.threshold": 0.7,
        "clarification.max_attempts": 2,
    }
    
    with patch("src.llm.clarification_manager.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def mock_logger():
    """
    Mock logger to avoid actual logging during tests.
    
    Testing Concept: Mock logging
    """
    with patch("src.llm.clarification_manager.logger") as mock:
        yield mock


@pytest.fixture
def mock_llm_orchestrator():
    """
    Mock LLM orchestrator.
    
    Testing Concept: Mock external LLM API calls
    """
    mock_orchestrator = MagicMock()
    
    # Mock send_messages to return clarifying question
    mock_orchestrator.send_messages = MagicMock(
        return_value=("Could you please clarify what you mean?", {})
    )
    
    return mock_orchestrator


@pytest.fixture
def mock_prompt_builder():
    """
    Mock PromptBuilder.
    
    Testing Concept: Mock prompt building
    """
    mock_builder = MagicMock()
    
    # Mock build_clarification_messages
    mock_builder.build_clarification_messages = MagicMock(
        return_value=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Generate a clarifying question."}
        ]
    )
    
    return mock_builder


@pytest.fixture
def clarification_manager(mock_config, mock_logger, mock_llm_orchestrator):
    """
    Create ClarificationManager with mocked dependencies.
    
    Testing Concept: Fixture with dependency injection
    """
    with patch("src.llm.clarification_manager.LLMOrchestrator") as mock_llm_class:
        mock_llm_class.return_value = mock_llm_orchestrator
        
        manager = ClarificationManager()
        manager.llm_orchestrator = mock_llm_orchestrator
        
        return manager


@pytest.fixture
def low_confidence_result():
    """Create a low confidence result for testing."""
    return ConfidenceResult(
        overall_confidence=0.5,
        retrieval_confidence=0.6,
        llm_confidence=0.4,
        is_confident=False,  
        confidence_breakdown={"reasoning": "Low confidence due to ambiguous query"}
    )

@pytest.fixture
def high_confidence_result():
    """Create a high confidence result for testing."""
    return ConfidenceResult(
        overall_confidence=0.85,
        retrieval_confidence=0.9,
        llm_confidence=0.8,
        is_confident=True,  
        confidence_breakdown={"reasoning": "High confidence"}  
    )

@pytest.fixture
def sample_retrieval_results():
    """Create sample retrieval results."""
    return [
        RetrievalResult(
            content="Schengen visa allows travel in 27 European countries.",
            relevance_score=0.85,  
            metadata={"source": "doc1"}
        ),
        RetrievalResult(
            content="You need valid passport for Schengen visa application.",
            relevance_score=0.75, 
            metadata={"source": "doc2"}
        )
    ]


@pytest.fixture
def conversation_history_no_clarification():
    """
    Create conversation history without recent clarification.
    
    Testing Concept: Fixture for conversation context
    """
    return [
        {"role": "user", "content": "What is a Schengen visa?"},
        {"role": "assistant", "content": "A Schengen visa allows travel...", "metadata": {}},
        {"role": "user", "content": "Tell me more about requirements"},
    ]


@pytest.fixture
def conversation_history_with_clarification():
    """
    Create conversation history with recent clarification.
    
    Testing Concept: Fixture for edge case
    """
    return [
        {"role": "user", "content": "What documents needed?"},
        {
            "role": "assistant", 
            "content": "Could you clarify which type of visa?",
            "metadata": {"type": "clarification"}
        },
        {"role": "user", "content": "Tourist visa"},
    ]


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestClarificationManagerInitialization:
    """Test ClarificationManager initialization."""
    
    def test_initialization_creates_llm_orchestrator(self, mock_config, mock_logger):
        """
        Test that LLM orchestrator is initialized.
        
        Testing Concept: Verify dependency creation
        """
        with patch("src.llm.clarification_manager.LLMOrchestrator") as mock_llm:
            manager = ClarificationManager()
            
            mock_llm.assert_called_once()
            assert manager.llm_orchestrator is not None
    
    def test_initialization_loads_confidence_threshold(self, mock_logger):
        """
        Test that confidence threshold is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.llm.clarification_manager.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.threshold": 0.75,
                "clarification.max_attempts": 3,
            }.get(key, default)
            
            with patch("src.llm.clarification_manager.LLMOrchestrator"):
                manager = ClarificationManager()
                
                assert manager.confidence_threshold == 0.75
    
    def test_initialization_loads_max_attempts(self, mock_logger):
        """
        Test that max_attempts is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.llm.clarification_manager.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "confidence.threshold": 0.7,
                "clarification.max_attempts": 5,
            }.get(key, default)
            
            with patch("src.llm.clarification_manager.LLMOrchestrator"):
                manager = ClarificationManager()
                
                assert manager.max_attempts == 5
    
    def test_initialization_sets_attempt_count_to_zero(
        self, mock_config, mock_logger
    ):
        """
        Test that attempt count starts at zero.
        
        Testing Concept: Test initial state
        """
        with patch("src.llm.clarification_manager.LLMOrchestrator"):
            manager = ClarificationManager()
            
            # Access private attribute for testing
            assert manager._ClarificationManager__attempt_count == 0


# ============================================================================
# TEST CLASS: Should Clarify - Happy Path
# ============================================================================


class TestShouldClarifyHappyPath:
    """Test should_clarify decision logic."""
    
    def test_should_clarify_returns_true_for_low_confidence(
        self, clarification_manager, low_confidence_result, 
        conversation_history_no_clarification
    ):
        """
        Test that clarification is needed for low confidence.
        
        Testing Concept: Happy path - normal clarification trigger
        """
        result = clarification_manager.should_clarify(
            low_confidence_result, 
            conversation_history_no_clarification
        )
        
        assert result is True
    
    def test_should_clarify_returns_false_for_high_confidence(
        self, clarification_manager, high_confidence_result,
        conversation_history_no_clarification
    ):
        """
        Test that clarification is not needed for high confidence.
        
        Testing Concept: Test negative condition
        """
        result = clarification_manager.should_clarify(
            high_confidence_result,
            conversation_history_no_clarification
        )
        
        assert result is False
    
    def test_should_clarify_at_threshold_boundary(
        self, clarification_manager, conversation_history_no_clarification
    ):
        """
        Test behavior exactly at confidence threshold.
        
        Testing Concept: Test boundary condition
        """
        # Confidence exactly at threshold (0.7)
        at_threshold = ConfidenceResult(
            overall_confidence=0.7,
            retrieval_confidence=0.7,
            llm_confidence=0.7,
            is_confident=False,
            confidence_breakdown={"reasoning": "At threshold"}
        )
        
        result = clarification_manager.should_clarify(
            at_threshold,
            conversation_history_no_clarification
        )
        
        # At threshold should not clarify (< threshold required)
        assert result is False
    
    def test_should_clarify_just_below_threshold(
        self, clarification_manager, conversation_history_no_clarification
    ):
        """
        Test behavior just below confidence threshold.
        
        Testing Concept: Test boundary - 1
        """
        just_below = ConfidenceResult(
            overall_confidence=0.69,  # Just below 0.7
            retrieval_confidence=0.7,
            llm_confidence=0.68,
            is_confident=False,
            confidence_breakdown={"reasoning": "Just below threshold"}
        )
        
        result = clarification_manager.should_clarify(
            just_below,
            conversation_history_no_clarification
        )
        
        assert result is True
    
    def test_should_clarify_with_empty_conversation_history(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test with empty conversation history.
        
        Testing Concept: Test empty list edge case
        """
        result = clarification_manager.should_clarify(
            low_confidence_result,
            []
        )
        
        # Should still clarify if confidence is low
        assert result is True
    
    def test_should_clarify_with_none_conversation_history(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test with None conversation history.
        
        Testing Concept: Test None input - should handle gracefully or raise error
        """
        # This test expects the code to handle None conversation_history
        # If the implementation doesn't handle None, this will fail
        with pytest.raises(TypeError, match="'NoneType' object is not reversible"):
            clarification_manager.should_clarify(
                low_confidence_result,
                None
            )


# ============================================================================
# TEST CLASS: Should Clarify - Attempt Limits
# ============================================================================


class TestShouldClarifyAttemptLimits:
    """Test attempt limit enforcement."""
    
    def test_should_clarify_returns_false_when_max_attempts_reached(
        self, clarification_manager, low_confidence_result,
        conversation_history_no_clarification
    ):
        """
        Test that clarification stops after max attempts.
        
        Testing Concept: Test limit enforcement
        """
        # Simulate reaching max attempts (2)
        clarification_manager._ClarificationManager__attempt_count = 2
        
        result = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_no_clarification
        )
        
        assert result is False
    
    def test_should_clarify_allows_up_to_max_attempts(
        self, clarification_manager, low_confidence_result,
        conversation_history_no_clarification
    ):
        """
        Test that clarification allowed up to max attempts.
        
        Testing Concept: Test boundary at limit
        """
        # At max - 1 (1 out of 2)
        clarification_manager._ClarificationManager__attempt_count = 1
        
        result = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_no_clarification
        )
        
        assert result is True
    
    def test_should_clarify_with_zero_attempts(
        self, clarification_manager, low_confidence_result,
        conversation_history_no_clarification
    ):
        """
        Test with zero attempts (initial state).
        
        Testing Concept: Test initial state
        """
        # Ensure count is 0
        clarification_manager._ClarificationManager__attempt_count = 0
        
        result = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_no_clarification
        )
        
        assert result is True
    
    def test_should_clarify_exceeding_max_attempts(
        self, clarification_manager, low_confidence_result,
        conversation_history_no_clarification
    ):
        """
        Test behavior when attempts exceed max.
        
        Testing Concept: Test over-limit condition
        """
        # Exceed max attempts
        clarification_manager._ClarificationManager__attempt_count = 5
        
        result = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_no_clarification
        )
        
        assert result is False


# ============================================================================
# TEST CLASS: Should Clarify - Conversation History Analysis
# ============================================================================


class TestShouldClarifyConversationAnalysis:
    """Test conversation history analysis logic."""
    
    def test_should_clarify_skips_if_last_assistant_was_clarification(
        self, clarification_manager, low_confidence_result,
        conversation_history_with_clarification, mock_logger
    ):
        """
        Test that clarification is skipped if last assistant message was clarification.
        
        Testing Concept: Test early return logic
        """
        result = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_with_clarification
        )
        
        # Should not clarify (last message was clarification)
        assert result is False
        
        # Should log debug message
        mock_logger.debug.assert_called_with(
            "Clarification skipped: last assistant message was a clarification"
        )
    
    def test_should_clarify_checks_only_last_assistant_message(
        self, clarification_manager, low_confidence_result, mock_logger
    ):
        """
        Test that only most recent assistant message is checked.
        
        Testing Concept: Test loop early break
        """
        # History with clarification, but not the last assistant message
        history = [
            {"role": "user", "content": "Question 1"},
            {
                "role": "assistant",
                "content": "Clarification?",
                "metadata": {"type": "clarification"}
            },
            {"role": "user", "content": "Answer"},
            {"role": "assistant", "content": "Normal response", "metadata": {}},
            {"role": "user", "content": "Another question"},
        ]
        
        result = clarification_manager.should_clarify(low_confidence_result, history)
        
        # Should clarify (last assistant was NOT clarification)
        assert result is True
    
    def test_should_clarify_detects_clarification_by_metadata(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test clarification detection via metadata.
        
        Testing Concept: Test metadata-based detection
        """
        history = [
            {"role": "user", "content": "Question"},
            {
                "role": "assistant",
                "content": "Any question",
                "metadata": {"type": "clarification"}  # Marked as clarification
            },
            {"role": "user", "content": "Response"},
        ]
        
        result = clarification_manager.should_clarify(low_confidence_result, history)
        
        assert result is False
    
    def test_should_clarify_with_missing_metadata_field(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test handling when metadata is missing 'type' field.
        
        Testing Concept: Test missing dict keys
        """
        history = [
            {"role": "user", "content": "Question"},
            {
                "role": "assistant",
                "content": "Response",
                "metadata": {"other_field": "value"}  # No 'type' field
            },
            {"role": "user", "content": "Follow-up"},
        ]
        
        result = clarification_manager.should_clarify(low_confidence_result, history)
        
        # Should clarify (no clarification detected)
        assert result is True
    
    def test_should_clarify_with_missing_metadata_dict(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test handling when metadata dict is missing.
        
        Testing Concept: Test missing optional field
        """
        history = [
            {"role": "user", "content": "Question"},
            {
                "role": "assistant",
                "content": "Response"
                # No metadata field at all
            },
            {"role": "user", "content": "Follow-up"},
        ]
        
        result = clarification_manager.should_clarify(low_confidence_result, history)
        
        # Should clarify (no metadata = no clarification)
        assert result is True
    
    def test_should_clarify_skips_user_messages_in_loop(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test that user messages are skipped when checking history.
        
        Testing Concept: Test loop filtering
        """
        history = [
            {"role": "user", "content": "User message 1"},
            {"role": "user", "content": "User message 2"},
            {"role": "assistant", "content": "Assistant response", "metadata": {}},
            {"role": "user", "content": "Current question"},
        ]
        
        result = clarification_manager.should_clarify(low_confidence_result, history)
        
        # Should check assistant message, not user messages
        assert result is True
    
    def test_should_clarify_with_history_containing_only_user_messages(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test with history containing no assistant messages.
        
        Testing Concept: Test loop with no match
        """
        history = [
            {"role": "user", "content": "Question 1"},
            {"role": "user", "content": "Question 2"},
        ]
        
        result = clarification_manager.should_clarify(low_confidence_result, history)
        
        # Should clarify (no assistant message to check)
        assert result is True


# ============================================================================
# TEST CLASS: Generate Clarifying Question - Happy Path
# ============================================================================


class TestGenerateClarifyingQuestionHappyPath:
    """Test clarifying question generation."""
    
    def test_generate_clarifying_question_returns_string(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that generated question is a string.
        
        Testing Concept: Test return type
        """
        result = clarification_manager.generate_clarifying_question(
            query="What documents do I need?",
            context=sample_retrieval_results,
            confidence_result=low_confidence_result
        )
        
        assert isinstance(result, str)
    
    def test_generate_clarifying_question_calls_prompt_builder(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that PromptBuilder is called to build messages.
        
        Testing Concept: Verify dependency interaction
        """
        with patch("src.llm.clarification_manager.PromptBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_clarification_messages.return_value = [
                {"role": "system", "content": "System prompt"}
            ]
            mock_builder_class.return_value = mock_builder
            
            clarification_manager.generate_clarifying_question(
                query="Test query",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            # Verify PromptBuilder was instantiated
            mock_builder_class.assert_called_once()
            
            # Verify build_clarification_messages was called
            mock_builder.build_clarification_messages.assert_called_once()
    
    def test_generate_clarifying_question_passes_correct_parameters(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that correct parameters are passed to PromptBuilder.
        
        Testing Concept: Test parameter passing
        """
        with patch("src.llm.clarification_manager.PromptBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_clarification_messages.return_value = []
            mock_builder_class.return_value = mock_builder
            
            query = "What is required?"
            conversation_history = [{"role": "user", "content": "Hi"}]
            
            clarification_manager.generate_clarifying_question(
                query=query,
                context=sample_retrieval_results,
                confidence_result=low_confidence_result,
                conversation_history=conversation_history
            )
            
            # Verify parameters
            call_args = mock_builder.build_clarification_messages.call_args
            assert call_args[1]["query"] == query
            assert call_args[1]["context"] == sample_retrieval_results
            assert call_args[1]["retrieval_confidence"] == low_confidence_result.retrieval_confidence
            assert call_args[1]["llm_confidence"] == low_confidence_result.llm_confidence
            assert call_args[1]["overall_confidence"] == low_confidence_result.overall_confidence
            assert call_args[1]["conversation_history"] == conversation_history
    
    def test_generate_clarifying_question_calls_llm_orchestrator(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that LLM orchestrator is called to generate question.
        
        Testing Concept: Verify LLM invocation
        """
        with patch("src.llm.clarification_manager.PromptBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            messages = [{"role": "user", "content": "Generate question"}]
            mock_builder.build_clarification_messages.return_value = messages
            mock_builder_class.return_value = mock_builder
            
            clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            # Verify send_messages was called with messages
            clarification_manager.llm_orchestrator.send_messages.assert_called_once_with(
                messages
            )
    
    def test_generate_clarifying_question_increments_attempt_count(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that attempt count is incremented.
        
        Testing Concept: Test state mutation
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            initial_count = clarification_manager._ClarificationManager__attempt_count
            
            clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            assert clarification_manager._ClarificationManager__attempt_count == initial_count + 1
    
    def test_generate_clarifying_question_strips_whitespace(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that generated question is stripped of whitespace.
        
        Testing Concept: Test data cleaning
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # Mock LLM to return question with whitespace
            clarification_manager.llm_orchestrator.send_messages.return_value = (
                "  Question with spaces?  \n", {}
            )
            
            result = clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            assert result == "Question with spaces?"
            assert not result.startswith(" ")
            assert not result.endswith(" ")
    
    def test_generate_clarifying_question_logs_context(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results, mock_logger
    ):
        """
        Test that context is logged for debugging.
        
        Testing Concept: Test logging
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            # Verify debug logging
            mock_logger.debug.assert_called_with(
                'Context for clarification LLM: %s',
                sample_retrieval_results
            )


# ============================================================================
# TEST CLASS: Generate Clarifying Question - Edge Cases
# ============================================================================


class TestGenerateClarifyingQuestionEdgeCases:
    """Test edge cases for question generation."""
    
    def test_generate_clarifying_question_with_empty_context(
        self, clarification_manager, low_confidence_result
    ):
        """
        Test with empty context list.
        
        Testing Concept: Test empty input
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            result = clarification_manager.generate_clarifying_question(
                query="Test",
                context=[],  # Empty context
                confidence_result=low_confidence_result
            )
            
            assert isinstance(result, str)
    
    def test_generate_clarifying_question_with_none_conversation_history(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test with None conversation history.
        
        Testing Concept: Test None optional parameter
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            result = clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result,
                conversation_history=None
            )
            
            assert isinstance(result, str)
    
    def test_generate_clarifying_question_with_empty_conversation_history(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test with empty conversation history.
        
        Testing Concept: Test empty list parameter
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            result = clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result,
                conversation_history=[]
            )
            
            assert isinstance(result, str)
    
    def test_generate_clarifying_question_with_very_long_query(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test with very long query.
        
        Testing Concept: Test large input
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            long_query = "What " * 1000  # Very long query
            
            result = clarification_manager.generate_clarifying_question(
                query=long_query,
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            assert isinstance(result, str)
    
    def test_generate_clarifying_question_with_zero_confidence(
        self, clarification_manager, sample_retrieval_results
    ):
        """
        Test with zero confidence values.
        
        Testing Concept: Test boundary value
        """
        zero_confidence = ConfidenceResult(
            overall_confidence=0.0,
            retrieval_confidence=0.0,
            llm_confidence=0.0,
            is_confident=False,
            confidence_breakdown={"reasoning": "Zero confidence"}
        )
        
        with patch("src.llm.clarification_manager.PromptBuilder"):
            result = clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=zero_confidence
            )
            
            assert isinstance(result, str)
    
    def test_generate_clarifying_question_multiple_calls_increment_count(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test that multiple calls increment attempt count.
        
        Testing Concept: Test cumulative state changes
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            initial_count = clarification_manager._ClarificationManager__attempt_count
            
            # Call multiple times
            for i in range(3):
                clarification_manager.generate_clarifying_question(
                    query=f"Test {i}",
                    context=sample_retrieval_results,
                    confidence_result=low_confidence_result
                )
            
            assert clarification_manager._ClarificationManager__attempt_count == initial_count + 3


# ============================================================================
# TEST CLASS: Generate Clarifying Question - Error Handling
# ============================================================================


class TestGenerateClarifyingQuestionErrorHandling:
    """Test error handling for question generation."""
    
    def test_generate_clarifying_question_with_llm_exception(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test behavior when LLM raises exception.
        
        Testing Concept: Test error propagation
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # Mock LLM to raise exception
            clarification_manager.llm_orchestrator.send_messages.side_effect = Exception(
                "LLM API error"
            )
            
            with pytest.raises(Exception, match="LLM API error"):
                clarification_manager.generate_clarifying_question(
                    query="Test",
                    context=sample_retrieval_results,
                    confidence_result=low_confidence_result
                )
    
    def test_generate_clarifying_question_with_prompt_builder_exception(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test behavior when PromptBuilder raises exception.
        
        Testing Concept: Test dependency failure
        """
        with patch("src.llm.clarification_manager.PromptBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_clarification_messages.side_effect = Exception(
                "Prompt build error"
            )
            mock_builder_class.return_value = mock_builder
            
            with pytest.raises(Exception, match="Prompt build error"):
                clarification_manager.generate_clarifying_question(
                    query="Test",
                    context=sample_retrieval_results,
                    confidence_result=low_confidence_result
                )
    
    def test_generate_clarifying_question_with_empty_llm_response(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test handling when LLM returns empty string.
        
        Testing Concept: Test malformed response
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # Mock LLM to return empty string
            clarification_manager.llm_orchestrator.send_messages.return_value = ("", {})
            
            result = clarification_manager.generate_clarifying_question(
                query="Test",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            
            # Should return empty string after strip
            assert result == ""


# ============================================================================
# TEST CLASS: Reset Attempts
# ============================================================================


class TestResetAttempts:
    """Test attempt count reset functionality."""
    
    def test_reset_attempts_sets_count_to_zero(
        self, clarification_manager
    ):
        """
        Test that reset_attempts sets count to zero.
        
        Testing Concept: Test state reset
        """
        # Set count to non-zero
        clarification_manager._ClarificationManager__attempt_count = 5
        
        clarification_manager.reset_attempts()
        
        assert clarification_manager._ClarificationManager__attempt_count == 0
    
    def test_reset_attempts_from_zero_stays_zero(
        self, clarification_manager
    ):
        """
        Test resetting when count is already zero.
        
        Testing Concept: Test idempotency
        """
        clarification_manager._ClarificationManager__attempt_count = 0
        
        clarification_manager.reset_attempts()
        
        assert clarification_manager._ClarificationManager__attempt_count == 0
    
    def test_reset_attempts_after_multiple_generations(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results
    ):
        """
        Test reset after generating multiple questions.
        
        Testing Concept: Test workflow integration
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # Generate multiple questions
            for _ in range(3):
                clarification_manager.generate_clarifying_question(
                    query="Test",
                    context=sample_retrieval_results,
                    confidence_result=low_confidence_result
                )
            
            # Verify count is 3
            assert clarification_manager._ClarificationManager__attempt_count == 3
            
            # Reset
            clarification_manager.reset_attempts()
            
            # Verify count is 0
            assert clarification_manager._ClarificationManager__attempt_count == 0
    
    def test_reset_attempts_allows_new_clarifications(
        self, clarification_manager, low_confidence_result,
        conversation_history_no_clarification
    ):
        """
        Test that reset allows new clarifications after max attempts.
        
        Testing Concept: Test reset effect on decision logic
        """
        # Reach max attempts
        clarification_manager._ClarificationManager__attempt_count = 2
        
        # Should not clarify (at max)
        result1 = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_no_clarification
        )
        assert result1 is False
        
        # Reset
        clarification_manager.reset_attempts()
        
        # Should now clarify again
        result2 = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_no_clarification
        )
        assert result2 is True


# ============================================================================
# TEST CLASS: Integration and Complex Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_clarification_workflow(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results, conversation_history_no_clarification
    ):
        """
        Test complete clarification workflow.
        
        Testing Concept: Integration test
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # 1. Check if should clarify
            should_clarify = clarification_manager.should_clarify(
                low_confidence_result,
                conversation_history_no_clarification
            )
            assert should_clarify is True
            
            # 2. Generate clarifying question
            question = clarification_manager.generate_clarifying_question(
                query="What documents?",
                context=sample_retrieval_results,
                confidence_result=low_confidence_result
            )
            assert isinstance(question, str)
            
            # 3. Verify attempt count incremented
            assert clarification_manager._ClarificationManager__attempt_count == 1
    
    def test_max_attempts_workflow(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results, conversation_history_no_clarification
    ):
        """
        Test workflow reaching max attempts.
        
        Testing Concept: Test limit enforcement workflow
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # Generate questions up to max attempts (2)
            for i in range(2):
                should_clarify = clarification_manager.should_clarify(
                    low_confidence_result,
                    conversation_history_no_clarification
                )
                assert should_clarify is True
                
                clarification_manager.generate_clarifying_question(
                    query=f"Question {i}",
                    context=sample_retrieval_results,
                    confidence_result=low_confidence_result
                )
            
            # Try to clarify again (should be blocked)
            should_clarify_again = clarification_manager.should_clarify(
                low_confidence_result,
                conversation_history_no_clarification
            )
            assert should_clarify_again is False
    
    def test_clarification_after_previous_clarification(
        self, clarification_manager, low_confidence_result,
        conversation_history_with_clarification
    ):
        """
        Test that clarification is skipped after previous clarification.
        
        Testing Concept: Test conversation flow logic
        """
        # Should not clarify (last assistant was clarification)
        should_clarify = clarification_manager.should_clarify(
            low_confidence_result,
            conversation_history_with_clarification
        )
        
        assert should_clarify is False
    
    def test_reset_and_retry_workflow(
        self, clarification_manager, low_confidence_result,
        sample_retrieval_results, conversation_history_no_clarification
    ):
        """
        Test reset and retry workflow.
        
        Testing Concept: Test state management workflow
        """
        with patch("src.llm.clarification_manager.PromptBuilder"):
            # Exhaust attempts
            for _ in range(2):
                clarification_manager.generate_clarifying_question(
                    query="Test",
                    context=sample_retrieval_results,
                    confidence_result=low_confidence_result
                )
            
            # Blocked by max attempts
            assert clarification_manager.should_clarify(
                low_confidence_result,
                conversation_history_no_clarification
            ) is False
            
            # Reset for new conversation
            clarification_manager.reset_attempts()
            
            # Now can clarify again
            assert clarification_manager.should_clarify(
                low_confidence_result,
                conversation_history_no_clarification
            ) is True


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("confidence,should_clarify", [
        (0.1, True),   # Very low
        (0.5, True),   # Low
        (0.69, True),  # Just below threshold
        (0.7, False),  # At threshold
        (0.8, False),  # Above threshold
        (0.95, False), # Very high
    ])
    def test_should_clarify_various_confidence_levels(
        self, clarification_manager, confidence, should_clarify
    ):
        """
        Test clarification decision at various confidence levels.
        
        Testing Concept: Parameterized boundary testing
        """
        confidence_result = ConfidenceResult(
            overall_confidence=confidence,
            retrieval_confidence=confidence,
            llm_confidence=confidence,
            is_confident=confidence >= 0.7,
            confidence_breakdown={"reasoning": "Test"}
        )
        
        result = clarification_manager.should_clarify(
            confidence_result,
            []  # Empty history
        )
        
        assert result == should_clarify
    
    @pytest.mark.parametrize("attempt_count,max_attempts,should_clarify", [
        (0, 2, True),   # Zero attempts
        (1, 2, True),   # One attempt
        (2, 2, False),  # At max
        (3, 2, False),  # Exceeded max
        (0, 5, True),   # Different max, zero attempts
        (4, 5, True),   # Different max, one below
        (5, 5, False),  # Different max, at limit
    ])
    def test_should_clarify_various_attempt_counts(
        self, clarification_manager, attempt_count, max_attempts, should_clarify
    ):
        """
        Test clarification decision with various attempt counts.
        
        Testing Concept: Parameterized limit testing
        """
        clarification_manager._ClarificationManager__attempt_count = attempt_count
        clarification_manager.max_attempts = max_attempts
        
        low_confidence = ConfidenceResult(
            overall_confidence=0.5,
            retrieval_confidence=0.5,
            llm_confidence=0.5,
            is_confident=False,
            confidence_breakdown={"reasoning": "Low confidence"}
        )
        
        result = clarification_manager.should_clarify(low_confidence, [])
        
        assert result == should_clarify


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.llm.clarification_manager",
        "--cov-report=term-missing"
    ])