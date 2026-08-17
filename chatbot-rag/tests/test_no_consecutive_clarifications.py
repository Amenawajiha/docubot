"""Test that prevents consecutive clarifications when user responds to clarification."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Message, ConfidenceResult


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_no_consecutive_clarifications(mock_websocket):
    """Test that system doesn't ask clarification right after user responds to clarification."""

    # Patch service manager and all dependencies
    with patch("src.response_manager.get_service_manager") as mock_sm, patch(
        "src.response_manager.get_config"
    ) as mock_config, patch("src.llm.clarification_manager.get_config") as mock_clarif_config:
        
        # Mock config values
        def config_side_effect(key, default=None):
            config_map = {
                "rag.low_cutoff": 0.0,
                "confidence.threshold": 0.5,
                "clarification.max_attempts": 2,
                "fallback.unknown_patterns": [
                    "i don't know",
                    "don't know",
                ],
            }
            return config_map.get(key, default)
        
        mock_config.side_effect = config_side_effect
        mock_clarif_config.side_effect = config_side_effect

        from src.response_manager import ResponseManager

        # Create mock service manager
        service_manager = MagicMock()
        mock_sm.return_value = service_manager

        # Mock vector retriever
        vector_retriever = MagicMock()
        vector_retriever.retrieve_with_reranking.return_value = [
            MagicMock(
                content="Low relevance content",
                metadata={"source": "test.pdf"},
                relevance_score=0.2,  # Low relevance
            )
        ]
        service_manager.get_vector_retriever.return_value = vector_retriever

        # Mock LLM orchestrator - returns "unknown" response for main queries,
        # and generates clarifying questions when asked
        llm_call_count = [0]

        def llm_side_effect(messages):
            llm_call_count[0] += 1
            # Check if this is a clarification generation request
            system_msg = messages[0].get("content", "") if messages else ""
            if "clarifying question" in system_msg.lower():
                # This is a request to generate a clarifying question
                return ("Which city do you need information for?", [{"token": "Which", "logprob": -0.1}])
            else:
                # This is a main query - return "unknown" response
                return ("I don't know the answer.", [{"token": "I", "logprob": -0.5}])

        llm_orchestrator = MagicMock()
        llm_orchestrator.send_messages.side_effect = llm_side_effect
        service_manager.get_llm_orchestrator.return_value = llm_orchestrator

        # Mock confidence scorer - always returns low confidence
        confidence_scorer = MagicMock()
        confidence_scorer.run.return_value = ConfidenceResult(
            retrieval_confidence=0.2,
            llm_confidence=0.3,
            overall_confidence=0.25,
            is_confident=False,
            confidence_breakdown={"retrieval": 0.2, "llm": 0.3},
        )
        service_manager.get_confidence_scorer.return_value = confidence_scorer

        # Use real prompt builder
        from src.llm.prompt_builder import PromptBuilder

        prompt_builder = PromptBuilder()
        service_manager.get_prompt_builder.return_value = prompt_builder

        # Use real clarification manager
        from src.llm.clarification_manager import ClarificationManager

        clarification_manager = ClarificationManager()
        service_manager.get_clarification_manager.return_value = (
            clarification_manager
        )

        # Create response manager
        manager = ResponseManager(mock_websocket, is_authenticated=False)
        user_id = 999

        # Clear any existing conversation for this user
        manager.conversation_manager.clear_conversation(user_id)

        # First query - should trigger clarification
        print("\n=== Query 1: Initial question ===")
        await manager.handle_query("what is the phone number?", user_id)

        # Verify first clarification was sent
        assert mock_websocket.send_json.call_count == 1
        first_call = mock_websocket.send_json.call_args[0][0]
        print(f"First response type: {first_call['type']}")
        print(f"First response: {first_call['content'][:100]}")
        assert first_call["type"] == "clarification"

        # Reset mock
        mock_websocket.send_json.reset_mock()

        # Second query - user responds with short answer "USA"
        # This should NOT trigger another clarification immediately
        print("\n=== Query 2: Short response to clarification ===")
        await manager.handle_query("USA", user_id)

        # Verify response was sent
        assert mock_websocket.send_json.call_count == 1
        second_call = mock_websocket.send_json.call_args[0][0]
        print(f"Second response type: {second_call['type']}")
        print(f"Second response: {second_call['content'][:100]}")

        # Should get an answer (with fallback contact info), NOT another clarification
        assert second_call["type"] == "answer", (
            f"Expected 'answer' type, got '{second_call['type']}'. "
            "System should not ask consecutive clarifications."
        )

        # The response should be the CONTACT_FALLBACK since confidence is low
        from src.llm.prompts import CONTACT_FALLBACK

        assert CONTACT_FALLBACK in second_call["content"], (
            "Expected fallback contact info in response when confidence is low "
            "and clarification was just asked"
        )

        print(f"\n✓ Test passed: No consecutive clarifications")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
