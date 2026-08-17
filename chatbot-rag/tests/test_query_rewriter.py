"""Test query rewriter with real conversation scenarios."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.query_rewriter import QueryRewriter
from src.utils import logger


def test_query_rewriter():
    """Test query rewriter with scenarios from conversation 11.json."""
    
    rewriter = QueryRewriter(context_window_size=5)
    
    print("\n" + "="*80)
    print("TESTING QUERY REWRITER")
    print("="*80)
    
    # Test Case 1: "all" after "give me all prices"
    print("\n--- Test Case 1: User says 'all' after asking for prices ---")
    history_1 = [
        {"role": "user", "content": "give me all prices"},
        {"role": "assistant", "content": "Here are the pricing details we have on file:\n\n- **Flight itinerary**: $40 per traveler (includes a 24‑hour service and covers up to 8 flights) [Source: Schengen Visa FAQs.docx]\n\nIf you're looking for prices for other services (e.g., hotel booking, travel insurance), let me know and I'll pull those up for you."},
    ]
    query_1 = "all"
    rewritten_1 = rewriter.rewrite_query(query_1, history_1)
    print(f"Original query: '{query_1}'")
    print(f"Rewritten query: '{rewritten_1}'")
    print(f"✓ PASS" if "prices" in rewritten_1.lower() and rewritten_1 != query_1 else "✗ FAIL")
    
    # Test Case 2: "yes, looking for prices for all other services"
    print("\n--- Test Case 2: User confirms they want all other services ---")
    history_2 = [
        {"role": "user", "content": "give me all prices"},
        {"role": "assistant", "content": "Here are the pricing details we have on file:\n\n- **Flight itinerary**: $40 per traveler\n\nIf you're looking for prices for other services (e.g., hotel booking, travel insurance), let me know and I'll pull those up for you."},
        {"role": "user", "content": "yes, looking for prices for all other services"},
    ]
    query_2 = "yes, looking for prices for all other services"
    rewritten_2 = rewriter.rewrite_query(query_2, history_2)
    print(f"Original query: '{query_2}'")
    print(f"Rewritten query: '{rewritten_2}'")
    print(f"Note: This query is explicit enough, may not need rewriting")
    
    # Test Case 3: "hotel booking as well"
    print("\n--- Test Case 3: User adds 'hotel booking as well' ---")
    history_3 = [
        {"role": "user", "content": "all"},
        {"role": "assistant", "content": "I only have the price for the flight‑itinerary service on file:\n\n- **Flight itinerary**: $40 per traveler"},
        {"role": "user", "content": "hotel booking as well"},
    ]
    query_3 = "hotel booking as well"
    rewritten_3 = rewriter.rewrite_query(query_3, history_3)
    print(f"Original query: '{query_3}'")
    print(f"Rewritten query: '{rewritten_3}'")
    print(f"✓ PASS" if ("hotel" in rewritten_3.lower() and 
                        ("flight" in rewritten_3.lower() or "price" in rewritten_3.lower()) and 
                        rewritten_3 != query_3) else "✗ FAIL")
    
    # Test Case 4: "hotel booking" after being asked for clarification
    print("\n--- Test Case 4: User specifies 'hotel booking' after clarification ---")
    history_4 = [
        {"role": "user", "content": "hotel booking as well"},
        {"role": "assistant", "content": "Could you clarify which service's price you're looking for—hotel booking, flight itinerary, travel insurance, or a combined package?"},
        {"role": "user", "content": "hotel booking"},
    ]
    query_4 = "hotel booking"
    rewritten_4 = rewriter.rewrite_query(query_4, history_4)
    print(f"Original query: '{query_4}'")
    print(f"Rewritten query: '{rewritten_4}'")
    print(f"Note: Short queries with specific service names might not need much rewriting")
    
    # Test Case 5: Normal query that doesn't need rewriting
    print("\n--- Test Case 5: Normal explicit query ---")
    history_5 = []
    query_5 = "What is the price of a flight itinerary?"
    rewritten_5 = rewriter.rewrite_query(query_5, history_5)
    print(f"Original query: '{query_5}'")
    print(f"Rewritten query: '{rewritten_5}'")
    print(f"✓ PASS" if rewritten_5 == query_5 else "✗ FAIL (should not rewrite explicit queries)")
    
    # Test Case 6: "price ?" followed by clarification then "all"
    print("\n--- Test Case 6: Vague 'price?' then clarification then 'all' ---")
    history_6 = [
        {"role": "user", "content": "price ?"},
        {"role": "assistant", "content": "I'm not sure which price you're referring to. Are you asking about the cost for:\n\n- a flight itinerary\n- a hotel booking\n- travel insurance\n\nor something else?"},
        {"role": "user", "content": "all"},
    ]
    query_6 = "all"
    rewritten_6 = rewriter.rewrite_query(query_6, history_6)
    print(f"Original query: '{query_6}'")
    print(f"Rewritten query: '{rewritten_6}'")
    print(f"✓ PASS" if ("price" in rewritten_6.lower() and 
                        ("flight" in rewritten_6.lower() or "hotel" in rewritten_6.lower() or "insurance" in rewritten_6.lower()) and
                        rewritten_6 != query_6) else "✗ FAIL")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_query_rewriter()
