"""
Regression tests for user queries using the chatbot's response generation.
These tests call the LLM pipeline with each query from test_user_queries.py
and check if the response has similar meaning to the expected response.
"""

import pytest
import difflib
from datetime import datetime, timezone
from tests.test_user_queries import test_cases
from src.response_manager import ResponseManager
from src.service_manager import ServiceManager
from src.models import Message
from src.utils.config_loader import ConfigLoader


@pytest.fixture(scope="module")
def response_manager():
    """Fixture to initialize the ResponseManager for testing."""
    config = ConfigLoader().load_config()
    service_manager = ServiceManager(config)
    return ResponseManager(service_manager)


@pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc["query"])
def test_query_response_similarity(response_manager, test_case):
    """
    Test that the chatbot's response to a query has similar meaning to the expected response.
    Uses sequence matching to check semantic similarity.
    """
    query = test_case["query"]
    expected_response = test_case["expected_response"]
    explanation = test_case["explanation"]

    # Create a conversation request (assuming user_id=999 for testing)
    request = Message(
        user_id=999,
        role="user",
        content=query,
        timestamp=datetime.now(timezone.utc),
        metadata={}
    )

    # Get the response from the chatbot
    response = response_manager.get_response(request)

    # Extract the assistant's content (assuming response has a 'content' field)
    actual_response = response.content if hasattr(response, 'content') else str(response)

    # Calculate similarity ratio
    similarity = difflib.SequenceMatcher(None, expected_response.lower(), actual_response.lower()).ratio()

    # Assert similarity is above a threshold (adjust as needed)
    threshold = 0.5  # 50% similarity for semantic matching
    assert similarity >= threshold, (
        f"Response for query '{query}' does not match expected meaning.\n"
        f"Expected: {expected_response}\n"
        f"Actual: {actual_response}\n"
        f"Similarity: {similarity:.2f}\n"
        f"Explanation: {explanation}"
    )

    # Additional check: Ensure key phrases from expected are somewhat present
    key_phrases = [phrase.strip() for phrase in expected_response.split('.') if phrase.strip()]
    matched_phrases = sum(1 for phrase in key_phrases if phrase.lower() in actual_response.lower())
    phrase_match_ratio = matched_phrases / len(key_phrases) if key_phrases else 1.0

    assert phrase_match_ratio >= 0.3, (
        f"Key phrases from expected response not sufficiently present.\n"
        f"Expected: {expected_response}\n"
        f"Actual: {actual_response}\n"
        f"Phrase match ratio: {phrase_match_ratio:.2f}"
    )