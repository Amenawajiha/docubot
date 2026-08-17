"""
Query rewriter for context-aware query expansion.

PROBLEM [SOLVED]:
    In multi-turn pricing queries, users often say ambiguous things like "all", 
    "hotel booking as well", or "yes" that lack context. When these short queries 
    are used directly for vector retrieval, they retrieve irrelevant or no results.
    
SOLUTION:
    This module detects ambiguous queries and rewrites them by incorporating context
    from the recent conversation history (last N turns). The rewritten query is then
    used for vector retrieval, ensuring better search results.
    
EXAMPLE:
    User: "give me all prices"
    Bot: "Here's the flight price..." (only retrieved flight info)
    User: "all"  ← Ambiguous!
    
    Before fix: Vector search for "all" → poor results
    After fix:  Rewritten to "What are the prices for all services: flight, hotel, insurance...?"
                → better retrieval → complete pricing info
                
See CONTEXT_MAINTENANCE_FIX.md for detailed analysis and testing results.
"""

from typing import Dict, List, Optional

from src.utils import logger


class QueryRewriter:
    """
    Rewrites ambiguous or incomplete queries by incorporating context from
    recent conversation history.
    
    This solves the context maintenance issue where short queries like "all",
    "hotel booking as well", or "yes" don't carry enough information on their own.
    """

    def __init__(self, context_window_size: int = 5):
        """
        Initialize query rewriter.
        
        Args:
            context_window_size: Number of recent conversation turns to consider (default: 5)
        """
        self.context_window_size = context_window_size
        
        # Keywords that indicate a query needs context from previous turns
        self.context_dependent_keywords = [
            "all", "both", "everything", "yes", "also", "as well",
            "too", "and", "what about", "how about", "it", "that",
            "them", "those", "these", "price", "prices", "cost", "costs",
        ]
        
        # Keywords related to pricing queries
        self.pricing_keywords = [
            "price", "prices", "cost", "costs", "fee", "fees",
            "charge", "charges", "how much", "pricing",
        ]
        
        # Service-related keywords
        self.service_keywords = [
            "flight", "itinerary", "hotel", "booking", "insurance",
            "travel", "visa", "document", "service", "services",
        ]

    def needs_rewriting(self, query: str) -> bool:
        """
        Check if a query is ambiguous and needs rewriting.
        
        Args:
            query: User query
            
        Returns:
            True if query needs rewriting, False otherwise
        """
        query_lower = query.lower().strip()
        
        # Check for explicit context-dependent phrases
        context_phrases = ["as well", "also", "too", "and"]
        for phrase in context_phrases:
            if phrase in query_lower:
                logger.debug("Query '%s' needs rewriting (contains phrase: %s)", query, phrase)
                return True
        
        # Very short queries likely need context
        if len(query_lower.split()) <= 3:
            # Check if it contains context-dependent keywords
            for keyword in self.context_dependent_keywords:
                if keyword in query_lower:
                    logger.debug("Query '%s' needs rewriting (contains keyword: %s)", query, keyword)
                    return True
        
        return False

    def rewrite_query(
        self,
        current_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Rewrite query by incorporating relevant context from conversation history.
        
        Args:
            current_query: The current user query
            conversation_history: List of recent conversation messages
            
        Returns:
            Rewritten query with context, or original query if no rewriting needed
        """
        if not conversation_history or not self.needs_rewriting(current_query):
            logger.debug("Query does not need rewriting: %s", current_query)
            return current_query
        
        # Get recent window of conversation
        recent_history = conversation_history[-self.context_window_size * 2:]  # *2 for user+assistant pairs
        
        # Extract relevant context
        pricing_context = self._extract_pricing_context(recent_history)
        service_context = self._extract_service_context(recent_history)
        
        # Build rewritten query
        rewritten = self._build_rewritten_query(
            current_query, pricing_context, service_context, recent_history
        )
        
        if rewritten != current_query:
            logger.info("Rewrote query from '%s' to '%s'", current_query, rewritten)
        
        return rewritten

    def _extract_pricing_context(self, history: List[Dict[str, str]]) -> Optional[str]:
        """
        Extract pricing-related context from conversation history.
        
        Args:
            history: Conversation history
            
        Returns:
            Pricing context string or None
        """
        for msg in reversed(history):
            if msg.get("role") == "user":
                content = msg.get("content")
                if content is None:
                    logger.debug("Skipping message with None content")
                    continue

                content_lower = content.lower()

                # Check if user asked about prices
                if any(keyword in content_lower for keyword in self.pricing_keywords):
                    logger.debug("Found pricing context in history: %s", msg.get("content"))
                    return content
        return None

    def _extract_service_context(self, history: List[Dict[str, str]]) -> List[str]:
        """
        Extract service-related mentions from conversation history.
        
        Args:
            history: Conversation history
            
        Returns:
            List of service keywords mentioned
        """
        services = []
        for msg in reversed(history):
            content = msg.get("content")
            if content is None:
                logger.debug("Skipping message with None content")
                continue

            content_lower = content.lower()

            for service in self.service_keywords:
                if service in content_lower and service not in services:
                    services.append(service)
        
        logger.debug("Found service context: %s", services)
        return services

    def _build_rewritten_query(
        self,
        current_query: str,
        pricing_context: Optional[str],
        service_context: List[str],
        history: List[Dict[str, str]],
    ) -> str:
        """
        Build the rewritten query by combining current query with context.
        
        Args:
            current_query: Original user query
            pricing_context: Pricing-related context from history
            service_context: Service keywords from history
            history: Full conversation history
            
        Returns:
            Rewritten query
        """
        query_lower = current_query.lower().strip()
        
        # Handle "all" or similar aggregate requests
        if query_lower in ["all", "all of them", "both", "everything", "yes"]:
            if pricing_context:
                # User wants all prices
                services_str = ", ".join(service_context) if service_context else "services"
                return f"What are the prices for all services: {services_str}?"
            else:
                # Look at last assistant message to understand what "all" refers to
                for msg in reversed(history):
                    if msg.get("role") == "assistant":
                        content = msg.get("content")
                        if content is None:
                            logger.debug("Skipping message with None content")
                            continue

                        # If assistant asked about specific things, include them
                        if "?" in content:
                            content_lower = content.lower()
                            # Extract the options from the question
                            if "flight" in content_lower or "hotel" in content_lower or "insurance" in content_lower:
                                return "What are the prices for flight itinerary, hotel booking, and travel insurance?"
                        break
        
        # Handle "X as well" or "also X" patterns
        if "as well" in query_lower or "also" in query_lower or "too" in query_lower:
            # Extract the new service being asked about
            new_service = None
            for service in self.service_keywords:
                if service in query_lower:
                    new_service = service
                    break
            
            if new_service and pricing_context:
                # Combine with previous pricing request
                return f"{pricing_context} and {new_service}"
            elif new_service and service_context:
                # Combine services
                all_services = service_context + [new_service]
                return f"What are the prices for {', '.join(all_services)}?"
        
        # Handle short pricing queries with context
        if len(query_lower.split()) <= 3 and any(k in query_lower for k in self.pricing_keywords):
            if service_context:
                services_str = ", ".join(service_context)
                return f"What are the prices for {services_str}?"
        
        # If we couldn't rewrite meaningfully, return original
        return current_query
