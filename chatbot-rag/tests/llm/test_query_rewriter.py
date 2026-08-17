"""
Comprehensive unit tests for QueryRewriter.

This test suite covers:
- Initialization and configuration
- Query rewriting detection (needs_rewriting)
- Query rewriting logic (rewrite_query)
- Context extraction (pricing and service)
- Query building logic
- Edge cases and error handling
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.llm.query_rewriter.logger") as mock:
        yield mock


@pytest.fixture
def query_rewriter(mock_logger):
    """Create QueryRewriter instance with default settings."""
    from src.llm.query_rewriter import QueryRewriter
    return QueryRewriter(context_window_size=5)


@pytest.fixture
def query_rewriter_small_window(mock_logger):
    """Create QueryRewriter with small context window."""
    from src.llm.query_rewriter import QueryRewriter
    return QueryRewriter(context_window_size=2)


@pytest.fixture
def pricing_conversation_history():
    """Create conversation history with pricing queries."""
    return [
        {"role": "user", "content": "give me all prices"},
        {"role": "assistant", "content": "Here are the pricing details:\n\n- **Flight itinerary**: $40 per traveler"},
        {"role": "user", "content": "what about hotel?"},
    ]


@pytest.fixture
def service_conversation_history():
    """Create conversation history mentioning various services."""
    return [
        {"role": "user", "content": "Tell me about flight itinerary"},
        {"role": "assistant", "content": "Flight itinerary costs $40 and includes hotel booking support."},
        {"role": "user", "content": "What about travel insurance?"},
    ]


@pytest.fixture
def clarification_conversation_history():
    """Create conversation history with assistant asking for clarification."""
    return [
        {"role": "user", "content": "price?"},
        {"role": "assistant", "content": "Are you asking about:\n- flight itinerary\n- hotel booking\n- travel insurance?"},
        {"role": "user", "content": "all"},
    ]


@pytest.fixture
def empty_conversation_history():
    """Create empty conversation history."""
    return []


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestQueryRewriterInitialization:
    """Test QueryRewriter initialization."""
    
    def test_initialization_with_default_context_window(self, mock_logger):
        """
        Test default context window size.
        
        Testing Concept: Test default parameter
        """
        from src.llm.query_rewriter import QueryRewriter
        rewriter = QueryRewriter()
        
        assert rewriter.context_window_size == 5
    
    def test_initialization_with_custom_context_window(self, mock_logger):
        """
        Test custom context window size.
        
        Testing Concept: Test parameter override
        """
        from src.llm.query_rewriter import QueryRewriter
        rewriter = QueryRewriter(context_window_size=10)
        
        assert rewriter.context_window_size == 10
    
    def test_initialization_with_zero_context_window(self, mock_logger):
        """
        Test with zero context window.
        
        Testing Concept: Test boundary value
        """
        from src.llm.query_rewriter import QueryRewriter
        rewriter = QueryRewriter(context_window_size=0)
        
        assert rewriter.context_window_size == 0
    
    def test_initialization_sets_context_dependent_keywords(self, mock_logger):
        """
        Test that context-dependent keywords are initialized.
        
        Testing Concept: Test attribute initialization
        """
        from src.llm.query_rewriter import QueryRewriter
        rewriter = QueryRewriter()
        
        assert isinstance(rewriter.context_dependent_keywords, list)
        assert len(rewriter.context_dependent_keywords) > 0
        assert "all" in rewriter.context_dependent_keywords
        assert "yes" in rewriter.context_dependent_keywords
    
    def test_initialization_sets_pricing_keywords(self, mock_logger):
        """
        Test that pricing keywords are initialized.
        
        Testing Concept: Test attribute initialization
        """
        from src.llm.query_rewriter import QueryRewriter
        rewriter = QueryRewriter()
        
        assert isinstance(rewriter.pricing_keywords, list)
        assert len(rewriter.pricing_keywords) > 0
        assert "price" in rewriter.pricing_keywords
        assert "cost" in rewriter.pricing_keywords
    
    def test_initialization_sets_service_keywords(self, mock_logger):
        """
        Test that service keywords are initialized.
        
        Testing Concept: Test attribute initialization
        """
        from src.llm.query_rewriter import QueryRewriter
        rewriter = QueryRewriter()
        
        assert isinstance(rewriter.service_keywords, list)
        assert len(rewriter.service_keywords) > 0
        assert "flight" in rewriter.service_keywords
        assert "hotel" in rewriter.service_keywords


# ============================================================================
# TEST CLASS: Needs Rewriting - Happy Path
# ============================================================================


class TestNeedsRewritingHappyPath:
    """Test needs_rewriting detection logic."""
    
    def test_needs_rewriting_returns_true_for_as_well(self, query_rewriter, mock_logger):
        """
        Test that 'as well' triggers rewriting.
        
        Testing Concept: Test context-dependent phrase detection
        """
        result = query_rewriter.needs_rewriting("hotel booking as well")
        
        assert result is True
        mock_logger.debug.assert_called()
    
    def test_needs_rewriting_returns_true_for_also(self, query_rewriter, mock_logger):
        """
        Test that 'also' triggers rewriting.
        
        Testing Concept: Test context-dependent phrase detection
        """
        result = query_rewriter.needs_rewriting("also show me prices")
        
        assert result is True
    
    def test_needs_rewriting_returns_true_for_too(self, query_rewriter, mock_logger):
        """
        Test that 'too' triggers rewriting.
        
        Testing Concept: Test context-dependent phrase detection
        """
        result = query_rewriter.needs_rewriting("that too")
        
        assert result is True
    
    def test_needs_rewriting_returns_true_for_short_query_with_all(self, query_rewriter, mock_logger):
        """
        Test that short query with 'all' triggers rewriting.
        
        Testing Concept: Test short query detection
        """
        result = query_rewriter.needs_rewriting("all")
        
        assert result is True
    
    def test_needs_rewriting_returns_true_for_short_query_with_yes(self, query_rewriter, mock_logger):
        """
        Test that short query with 'yes' triggers rewriting.
        
        Testing Concept: Test short query detection
        """
        result = query_rewriter.needs_rewriting("yes")
        
        assert result is True
    
    def test_needs_rewriting_returns_true_for_short_query_with_price(self, query_rewriter, mock_logger):
        """
        Test that short query with 'price' triggers rewriting.
        
        Testing Concept: Test short query with keyword
        """
        result = query_rewriter.needs_rewriting("price?")
        
        assert result is True
    
    def test_needs_rewriting_returns_false_for_explicit_query(self, query_rewriter, mock_logger):
        """
        Test that explicit query doesn't trigger rewriting.
        
        Testing Concept: Test negative case
        """
        result = query_rewriter.needs_rewriting("What is the price of a flight itinerary?")
        
        assert result is False
    
    def test_needs_rewriting_returns_false_for_long_complete_query(self, query_rewriter, mock_logger):
        """
        Test that long complete query doesn't trigger rewriting.
        
        Testing Concept: Test query length threshold
        """
        result = query_rewriter.needs_rewriting("Can you tell me about visa requirements?")
        
        assert result is False
    
    def test_needs_rewriting_handles_case_insensitivity(self, query_rewriter, mock_logger):
        """
        Test that detection is case-insensitive.
        
        Testing Concept: Test case handling
        """
        result1 = query_rewriter.needs_rewriting("ALL")
        result2 = query_rewriter.needs_rewriting("All")
        result3 = query_rewriter.needs_rewriting("all")
        
        assert result1 is True
        assert result2 is True
        assert result3 is True


# ============================================================================
# TEST CLASS: Needs Rewriting - Edge Cases
# ============================================================================


class TestNeedsRewritingEdgeCases:
    """Test edge cases for needs_rewriting."""
    
    def test_needs_rewriting_with_empty_string(self, query_rewriter, mock_logger):
        """
        Test with empty string.
        
        Testing Concept: Test empty input
        """
        result = query_rewriter.needs_rewriting("")
        
        assert result is False
    
    def test_needs_rewriting_with_whitespace_only(self, query_rewriter, mock_logger):
        """
        Test with whitespace only.
        
        Testing Concept: Test whitespace handling
        """
        result = query_rewriter.needs_rewriting("   ")
        
        assert result is False
    
    def test_needs_rewriting_with_exactly_three_words(self, query_rewriter, mock_logger):
        """
        Test boundary at 3 words (threshold).
        
        Testing Concept: Test boundary condition
        """
        result = query_rewriter.needs_rewriting("all the prices")
        
        assert result is True  # Has keyword "all" and "prices"
    
    def test_needs_rewriting_with_four_words_no_keywords(self, query_rewriter, mock_logger):
        """
        Test query with 4 words and no keywords.
        
        Testing Concept: Test over threshold without keywords
        """
        result = query_rewriter.needs_rewriting("tell me about documents")
        
        assert result is False
    
    def test_needs_rewriting_with_special_characters(self, query_rewriter, mock_logger):
        """
        Test query with special characters.
        
        Testing Concept: Test special character handling
        """
        result = query_rewriter.needs_rewriting("all?!?")
        
        assert result is True
    
    def test_needs_rewriting_with_multiple_spaces(self, query_rewriter, mock_logger):
        """
        Test query with multiple spaces between words.
        
        Testing Concept: Test whitespace normalization
        """
        result = query_rewriter.needs_rewriting("all    of    them")
        
        # Word count should still work with multiple spaces
        assert result is True


# ============================================================================
# TEST CLASS: Rewrite Query - Happy Path
# ============================================================================


class TestRewriteQueryHappyPath:
    """Test query rewriting logic."""
    
    def test_rewrite_query_returns_original_if_not_needed(
        self, query_rewriter, pricing_conversation_history, mock_logger
    ):
        """
        Test that explicit queries are not rewritten.
        
        Testing Concept: Test early return
        """
        query = "What is the price of a flight itinerary?"
        
        result = query_rewriter.rewrite_query(query, pricing_conversation_history)
        
        assert result == query
    
    def test_rewrite_query_returns_original_if_no_history(
        self, query_rewriter, mock_logger
    ):
        """
        Test that query is not rewritten without history.
        
        Testing Concept: Test None history
        """
        query = "all"
        
        result = query_rewriter.rewrite_query(query, None)
        
        assert result == query
    
    def test_rewrite_query_returns_original_if_empty_history(
        self, query_rewriter, empty_conversation_history, mock_logger
    ):
        """
        Test that query is not rewritten with empty history.
        
        Testing Concept: Test empty list
        """
        query = "all"
        
        result = query_rewriter.rewrite_query(query, empty_conversation_history)
        
        assert result == query
    
    def test_rewrite_query_expands_all_with_pricing_context(
        self, query_rewriter, pricing_conversation_history, mock_logger
    ):
        """
        Test that 'all' is expanded with pricing context.
        
        Testing Concept: Test query expansion
        """
        query = "all"
        
        result = query_rewriter.rewrite_query(query, pricing_conversation_history)
        
        assert result != query
        assert "price" in result.lower()
        assert "services" in result.lower()
    
    def test_rewrite_query_expands_as_well_pattern(
        self, query_rewriter, pricing_conversation_history, mock_logger
    ):
        """
        Test that 'X as well' pattern is expanded.
        
        Testing Concept: Test pattern recognition
        """
        query = "hotel booking as well"
        
        result = query_rewriter.rewrite_query(query, pricing_conversation_history)
        
        assert result != query
        assert "hotel" in result.lower()
    
    def test_rewrite_query_combines_services_for_as_well(
        self, query_rewriter, service_conversation_history, mock_logger
    ):
        """
        Test that services are combined for 'as well' pattern.
        
        Testing Concept: Test context combination
        """
        query = "insurance as well"
        
        result = query_rewriter.rewrite_query(query, service_conversation_history)
        
        assert result != query
        # Should include multiple services
        assert "price" in result.lower() or "insurance" in result.lower()
    
    def test_rewrite_query_logs_rewriting_action(
        self, query_rewriter, pricing_conversation_history, mock_logger
    ):
        """
        Test that rewriting is logged.
        
        Testing Concept: Test logging
        """
        query = "all"
        
        query_rewriter.rewrite_query(query, pricing_conversation_history)
        
        # Should log the rewriting
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0]
        assert "Rewrote query from" in call_args[0]


# ============================================================================
# TEST CLASS: Rewrite Query - Specific Patterns
# ============================================================================


class TestRewriteQueryPatterns:
    """Test specific query rewriting patterns."""
    
    def test_rewrite_query_all_pattern(self, query_rewriter, pricing_conversation_history, mock_logger):
        """Test rewriting 'all' pattern."""
        result = query_rewriter.rewrite_query("all", pricing_conversation_history)
        
        assert result != "all"
        assert "price" in result.lower()
    
    def test_rewrite_query_both_pattern(self, query_rewriter, pricing_conversation_history, mock_logger):
        """Test rewriting 'both' pattern."""
        result = query_rewriter.rewrite_query("both", pricing_conversation_history)
        
        assert result != "both"
    
    def test_rewrite_query_everything_pattern(self, query_rewriter, pricing_conversation_history, mock_logger):
        """Test rewriting 'everything' pattern."""
        result = query_rewriter.rewrite_query("everything", pricing_conversation_history)
        
        assert result != "everything"
    
    def test_rewrite_query_yes_pattern(self, query_rewriter, pricing_conversation_history, mock_logger):
        """Test rewriting 'yes' pattern."""
        result = query_rewriter.rewrite_query("yes", pricing_conversation_history)
        
        assert result != "yes"
    
    def test_rewrite_query_all_of_them_pattern(self, query_rewriter, pricing_conversation_history, mock_logger):
        """Test rewriting 'all of them' pattern."""
        result = query_rewriter.rewrite_query("all of them", pricing_conversation_history)
        
        assert result != "all of them"
    
    def test_rewrite_query_also_pattern(self, query_rewriter, service_conversation_history, mock_logger):
        """Test rewriting 'also X' pattern."""
        result = query_rewriter.rewrite_query("also hotel", service_conversation_history)
        
        assert result != "also hotel"
        assert "hotel" in result.lower()
    
    def test_rewrite_query_too_pattern(self, query_rewriter, service_conversation_history, mock_logger):
        """Test rewriting 'X too' pattern."""
        result = query_rewriter.rewrite_query("hotel too", service_conversation_history)
        
        assert result != "hotel too"
        assert "hotel" in result.lower()


# ============================================================================
# TEST CLASS: Rewrite Query - With Clarification History
# ============================================================================


class TestRewriteQueryWithClarification:
    """Test query rewriting with assistant clarification questions."""
    
    def test_rewrite_query_uses_assistant_options(
        self, query_rewriter, clarification_conversation_history, mock_logger
    ):
        """
        Test that assistant's clarification options are used.
        
        Testing Concept: Test assistant message parsing
        """
        query = "all"
        
        result = query_rewriter.rewrite_query(query, clarification_conversation_history)
        
        assert result != query
        # Should extract options from assistant question
        assert any(service in result.lower() for service in ["flight", "hotel", "insurance"])
    
    def test_rewrite_query_detects_services_in_assistant_question(
        self, query_rewriter, mock_logger
    ):
        """
        Test service detection from assistant's question.
        
        Testing Concept: Test pattern extraction
        """
        history = [
            {"role": "user", "content": "price?"},
            {"role": "assistant", "content": "Do you mean flight or hotel?"},
            {"role": "user", "content": "all"},
        ]
        
        result = query_rewriter.rewrite_query("all", history)
        
        assert result != "all"
        assert "flight" in result.lower() or "hotel" in result.lower()


# ============================================================================
# TEST CLASS: Extract Pricing Context
# ============================================================================


class TestExtractPricingContext:
    """Test pricing context extraction."""
    
    def test_extract_pricing_context_finds_pricing_query(
        self, query_rewriter, pricing_conversation_history, mock_logger
    ):
        """
        Test extraction of pricing-related queries.
        
        Testing Concept: Test context extraction
        """
        context = query_rewriter._extract_pricing_context(pricing_conversation_history)
        
        assert context is not None
        assert "price" in context.lower()
    
    def test_extract_pricing_context_returns_most_recent(
        self, query_rewriter, mock_logger
    ):
        """
        Test that most recent pricing query is returned.
        
        Testing Concept: Test reverse iteration
        """
        history = [
            {"role": "user", "content": "what is the price?"},
            {"role": "assistant", "content": "The flight costs $40."},
            {"role": "user", "content": "how much does hotel cost?"},
        ]
        
        context = query_rewriter._extract_pricing_context(history)
        
        assert context is not None
        assert "hotel" in context.lower()
    
    def test_extract_pricing_context_returns_none_if_no_pricing(
        self, query_rewriter, mock_logger
    ):
        """
        Test that None is returned without pricing context.
        
        Testing Concept: Test negative case
        """
        history = [
            {"role": "user", "content": "tell me about visas"},
            {"role": "assistant", "content": "Visa info..."},
        ]
        
        context = query_rewriter._extract_pricing_context(history)
        
        assert context is None
    
    def test_extract_pricing_context_ignores_assistant_messages(
        self, query_rewriter, mock_logger
    ):
        """
        Test that only user messages are checked.
        
        Testing Concept: Test role filtering
        """
        history = [
            {"role": "assistant", "content": "The price is $40."},
            {"role": "user", "content": "tell me about documents"},
        ]
        
        context = query_rewriter._extract_pricing_context(history)
        
        # Should not find pricing context (only assistant mentioned price)
        assert context is None
    
    def test_extract_pricing_context_with_empty_history(
        self, query_rewriter, mock_logger
    ):
        """
        Test with empty history.
        
        Testing Concept: Test empty input
        """
        context = query_rewriter._extract_pricing_context([])
        
        assert context is None
    
    def test_extract_pricing_context_with_various_pricing_keywords(
        self, query_rewriter, mock_logger
    ):
        """
        Test detection of various pricing keywords.
        
        Testing Concept: Test keyword variations
        """
        keywords = ["price", "cost", "fee", "charge", "how much"]
        
        for keyword in keywords:
            history = [{"role": "user", "content": f"what is the {keyword}?"}]
            context = query_rewriter._extract_pricing_context(history)
            
            assert context is not None, f"Failed to detect keyword: {keyword}"


# ============================================================================
# TEST CLASS: Extract Service Context
# ============================================================================


class TestExtractServiceContext:
    """Test service context extraction."""
    
    def test_extract_service_context_finds_services(
        self, query_rewriter, service_conversation_history, mock_logger
    ):
        """
        Test extraction of service keywords.
        
        Testing Concept: Test keyword extraction
        """
        services = query_rewriter._extract_service_context(service_conversation_history)
        
        assert isinstance(services, list)
        assert len(services) > 0
        assert any(s in ["flight", "hotel", "insurance"] for s in services)
    
    def test_extract_service_context_removes_duplicates(
        self, query_rewriter, mock_logger
    ):
        """
        Test that duplicate services are removed.
        
        Testing Concept: Test deduplication
        """
        history = [
            {"role": "user", "content": "tell me about flight"},
            {"role": "assistant", "content": "Flight info..."},
            {"role": "user", "content": "more about flight"},
        ]
        
        services = query_rewriter._extract_service_context(history)
        
        # Should only have 'flight' once
        assert services.count("flight") == 1
    
    def test_extract_service_context_returns_empty_list_if_none(
        self, query_rewriter, mock_logger
    ):
        """
        Test that empty list is returned without services.
        
        Testing Concept: Test negative case
        """
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        
        services = query_rewriter._extract_service_context(history)
        
        assert services == []
    
    def test_extract_service_context_with_empty_history(
        self, query_rewriter, mock_logger
    ):
        """
        Test with empty history.
        
        Testing Concept: Test empty input
        """
        services = query_rewriter._extract_service_context([])
        
        assert services == []
    
    def test_extract_service_context_checks_all_messages(
        self, query_rewriter, mock_logger
    ):
        """
        Test that both user and assistant messages are checked.
        
        Testing Concept: Test comprehensive checking
        """
        history = [
            {"role": "user", "content": "tell me about flight"},
            {"role": "assistant", "content": "Also hotel is available"},
            {"role": "user", "content": "what about insurance?"},
        ]
        
        services = query_rewriter._extract_service_context(history)
        
        # Should find all three services
        assert "flight" in services
        assert "hotel" in services
        assert "insurance" in services
    
    def test_extract_service_context_case_insensitive(
        self, query_rewriter, mock_logger
    ):
        """
        Test that detection is case-insensitive.
        
        Testing Concept: Test case handling
        """
        history = [
            {"role": "user", "content": "FLIGHT and HOTEL"},
        ]
        
        services = query_rewriter._extract_service_context(history)
        
        assert "flight" in services
        assert "hotel" in services


# ============================================================================
# TEST CLASS: Build Rewritten Query
# ============================================================================


class TestBuildRewrittenQuery:
    """Test query building logic."""
    
    def test_build_rewritten_query_all_with_pricing_context(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for 'all' with pricing context.
        
        Testing Concept: Test query construction
        """
        result = query_rewriter._build_rewritten_query(
            "all",
            "what are the prices?",
            ["flight", "hotel"],
            []
        )
        
        assert result != "all"
        assert "price" in result.lower()
        assert "services" in result.lower()
    
    def test_build_rewritten_query_all_without_pricing_context(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for 'all' without pricing context.
        
        Testing Concept: Test fallback logic
        """
        history = [
            {"role": "assistant", "content": "Do you want flight or hotel?"},
        ]
        
        result = query_rewriter._build_rewritten_query(
            "all",
            None,
            [],
            history
        )
        
        # Should use assistant's question for context
        assert result != "all"
    
    def test_build_rewritten_query_as_well_with_pricing_context(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for 'X as well' with pricing context.
        
        Testing Concept: Test pattern combination
        """
        result = query_rewriter._build_rewritten_query(
            "hotel as well",
            "what is the price?",
            ["flight"],
            []
        )
        
        assert result != "hotel as well"
        assert "hotel" in result.lower()
    
    def test_build_rewritten_query_as_well_with_service_context(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for 'X as well' with service context.
        
        Testing Concept: Test service combination
        """
        result = query_rewriter._build_rewritten_query(
            "insurance as well",
            None,
            ["flight", "hotel"],
            []
        )
        
        assert result != "insurance as well"
        assert "insurance" in result.lower()
        assert "flight" in result.lower() or "price" in result.lower()
    
    def test_build_rewritten_query_short_pricing_query(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for short pricing queries.
        
        Testing Concept: Test short query expansion
        """
        result = query_rewriter._build_rewritten_query(
            "price?",
            None,
            ["flight", "hotel"],
            []
        )
        
        assert result != "price?"
        assert "price" in result.lower()
        assert "flight" in result.lower()
    
    def test_build_rewritten_query_returns_original_if_no_match(
        self, query_rewriter, mock_logger
    ):
        """
        Test that original query is returned if no rewriting pattern matches.
        
        Testing Concept: Test fallback
        """
        result = query_rewriter._build_rewritten_query(
            "some random query",
            None,
            [],
            []
        )
        
        assert result == "some random query"
    
    def test_build_rewritten_query_yes_with_services(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for 'yes' with service context.
        
        Testing Concept: Test affirmative expansion
        """
        result = query_rewriter._build_rewritten_query(
            "yes",
            "what are the prices?",
            ["flight", "hotel", "insurance"],
            []
        )
        
        assert result != "yes"
        assert "price" in result.lower()
        assert "services" in result.lower()
    
    def test_build_rewritten_query_both_pattern(
        self, query_rewriter, mock_logger
    ):
        """
        Test building query for 'both' pattern.
        
        Testing Concept: Test alternative aggregate keyword
        """
        result = query_rewriter._build_rewritten_query(
            "both",
            "what are the costs?",
            ["flight", "hotel"],
            []
        )
        
        assert result != "both"
        assert "price" in result.lower() or "cost" in result.lower()


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_pricing_workflow(self, query_rewriter, mock_logger):
        """
        Test complete pricing query workflow.
        
        Testing Concept: Integration test
        """
        # Conversation flow
        history = []
        
        # User asks for all prices
        history.append({"role": "user", "content": "give me all prices"})
        history.append({"role": "assistant", "content": "Flight costs $40"})
        
        # User says "all" (ambiguous)
        query = "all"
        result = query_rewriter.rewrite_query(query, history)
        
        assert result != query
        assert "price" in result.lower()
    
    def test_as_well_workflow(self, query_rewriter, mock_logger):
        """
        Test 'as well' pattern workflow.
        
        Testing Concept: Integration test
        """
        history = [
            {"role": "user", "content": "flight price?"},
            {"role": "assistant", "content": "Flight is $40"},
            {"role": "user", "content": "hotel as well"},
        ]
        
        query = "hotel as well"
        result = query_rewriter.rewrite_query(query, history)
        
        assert result != query
        assert "hotel" in result.lower()
    
    def test_clarification_then_all_workflow(self, query_rewriter, mock_logger):
        """
        Test clarification followed by 'all'.
        
        Testing Concept: Test clarification handling
        """
        history = [
            {"role": "user", "content": "price?"},
            {"role": "assistant", "content": "Which service? Flight, hotel, or insurance?"},
            {"role": "user", "content": "all"},
        ]
        
        result = query_rewriter.rewrite_query("all", history)
        
        assert result != "all"
        assert any(s in result.lower() for s in ["flight", "hotel", "insurance"])
    
    def test_context_window_limits_history(self, query_rewriter_small_window, mock_logger):
        """
        Test that context window limits history used.
        
        Testing Concept: Test window size enforcement
        """
        # Create history longer than window
        history = [
            {"role": "user", "content": "old query about visa"},
            {"role": "assistant", "content": "Visa info"},
            {"role": "user", "content": "old query about documents"},
            {"role": "assistant", "content": "Document info"},
            {"role": "user", "content": "recent query about prices"},
            {"role": "assistant", "content": "Price info for flight"},
            {"role": "user", "content": "all"},
        ]
        
        # Window size is 2, so only last 4 messages should be used (2*2)
        result = query_rewriter_small_window.rewrite_query("all", history)
        
        # Should use recent context about prices, not old visa queries
        assert "price" in result.lower()


# ============================================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""
    
    def test_rewrite_query_with_malformed_history(self, query_rewriter, mock_logger):
        """
        Test with malformed conversation history.
        
        Testing Concept: Test data validation
        """
        history = [
            {"role": "user"},  # Missing content
            {"content": "test"},  # Missing role
            {},  # Empty dict
        ]
        
        # Should not crash
        result = query_rewriter.rewrite_query("all", history)
        
        # May return original or rewritten, but shouldn't error
        assert isinstance(result, str)
    
    def test_rewrite_query_with_none_content(self, query_rewriter, mock_logger):
        """
        Test with None content in history.
        
        Testing Concept: Test None handling
        """
        history = [
            {"role": "user", "content": None},
            {"role": "assistant", "content": "test"},
        ]
        
        # Should not crash
        result = query_rewriter.rewrite_query("all", history)
        
        assert isinstance(result, str)
    
    def test_rewrite_query_with_very_long_history(self, query_rewriter, mock_logger):
        """
        Test with very long conversation history.
        
        Testing Concept: Test scalability
        """
        # Create 100 messages
        history = []
        for i in range(100):
            history.append({"role": "user", "content": f"query {i}"})
            history.append({"role": "assistant", "content": f"response {i}"})
        
        # Should only use recent window
        result = query_rewriter.rewrite_query("all", history)
        
        assert isinstance(result, str)
    
    def test_rewrite_query_with_unicode_characters(self, query_rewriter, mock_logger):
        """
        Test with unicode characters.
        
        Testing Concept: Test unicode handling
        """
        history = [
            {"role": "user", "content": "цена? 价格? السعر?"},
            {"role": "assistant", "content": "Price is $40"},
        ]
        
        result = query_rewriter.rewrite_query("all", history)
        
        assert isinstance(result, str)
    
    def test_rewrite_query_with_special_characters_in_query(self, query_rewriter, mock_logger):
        """
        Test query with special characters.
        
        Testing Concept: Test special character handling
        """
        history = [
            {"role": "user", "content": "what are prices?"},
        ]
        
        result = query_rewriter.rewrite_query("all!@#$%", history)
        
        assert isinstance(result, str)
    
    def test_needs_rewriting_with_numeric_query(self, query_rewriter, mock_logger):
        """
        Test with numeric query.
        
        Testing Concept: Test non-text input
        """
        result = query_rewriter.needs_rewriting("123")
        
        assert result is False
    
    def test_extract_pricing_context_with_no_user_messages(self, query_rewriter, mock_logger):
        """
        Test pricing extraction with only assistant messages.
        
        Testing Concept: Test message filtering
        """
        history = [
            {"role": "assistant", "content": "The price is $40"},
            {"role": "assistant", "content": "Cost is $50"},
        ]
        
        context = query_rewriter._extract_pricing_context(history)
        
        assert context is None
    
    def test_extract_service_context_with_overlapping_keywords(self, query_rewriter, mock_logger):
        """
        Test service extraction with overlapping keywords.
        
        Testing Concept: Test keyword overlap
        """
        history = [
            {"role": "user", "content": "flight itinerary booking service"},
        ]
        
        services = query_rewriter._extract_service_context(history)
        
        # Should find multiple services
        assert "flight" in services
        assert "itinerary" in services
        assert "booking" in services
        assert "service" in services


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("query,should_rewrite", [
        ("all", True),
        ("both", True),
        ("everything", True),
        ("yes", True),
        ("as well", True),
        ("also", True),
        ("too", True),
        ("price?", True),
        ("What is the price of flight?", False),
        ("Tell me about documents", False),
        ("hello", False),
    ])
    def test_needs_rewriting_various_queries(self, query_rewriter, query, should_rewrite, mock_logger):
        """
        Test needs_rewriting with various queries.
        
        Testing Concept: Parameterized testing
        """
        result = query_rewriter.needs_rewriting(query)
        assert result == should_rewrite
    
    @pytest.mark.parametrize("keyword", [
        "price", "prices", "cost", "costs", "fee", "fees",
        "charge", "charges", "how much", "pricing"
    ])
    def test_extract_pricing_context_detects_all_pricing_keywords(
        self, query_rewriter, keyword, mock_logger
    ):
        """
        Test that all pricing keywords are detected.
        
        Testing Concept: Comprehensive keyword testing
        """
        history = [{"role": "user", "content": f"what is the {keyword}?"}]
        
        context = query_rewriter._extract_pricing_context(history)
        
        assert context is not None
    
    @pytest.mark.parametrize("service", [
        "flight", "itinerary", "hotel", "booking", "insurance",
        "travel", "visa", "document", "service", "services"
    ])
    def test_extract_service_context_detects_all_services(
        self, query_rewriter, service, mock_logger
    ):
        """
        Test that all service keywords are detected.
        
        Testing Concept: Comprehensive keyword testing
        """
        history = [{"role": "user", "content": f"tell me about {service}"}]
        
        services = query_rewriter._extract_service_context(history)
        
        assert service in services
    
    @pytest.mark.parametrize("aggregate_word", [
        "all", "both", "everything", "yes", "all of them"
    ])
    def test_build_rewritten_query_handles_all_aggregate_patterns(
        self, query_rewriter, aggregate_word, mock_logger
    ):
        """
        Test that all aggregate patterns are handled.
        
        Testing Concept: Pattern coverage
        """
        result = query_rewriter._build_rewritten_query(
            aggregate_word,
            "what are the prices?",
            ["flight", "hotel"],
            []
        )
        
        assert result != aggregate_word
        assert "price" in result.lower()


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.llm.query_rewriter",
        "--cov-report=term-missing"
    ])