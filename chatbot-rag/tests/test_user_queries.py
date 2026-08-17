"""
Test cases for user queries and expected responses.
Each test case includes a query, the expected response (or a representative one from conversations),
and an explanation of what the response should convey (for semantic similarity checks).
"""

test_cases = [
    {
        "query": "What is a Schengen visa?",
        "expected_response": "General Schengen info from LLM knowledge",
        "explanation": "Should provide basic informational content about what a Schengen visa is, based on general knowledge."
    },
    {
        "query": "Give me info",
        "expected_response": "Answer with relevant info",
        "explanation": "Should provide relevant information based on context or general knowledge if this is a follow-up query. Else, seek clarification."
    },
    {
        "query": "How much?",
        "expected_response": "What do you mean by 'itinerary'?",
        "explanation": "Should seek clarification when the query is ambiguous, asking for more details on what 'itinerary' refers to."
    },
    {
        "query": "What is the secret code?",
        "expected_response": "Sorry, I don't have a proper answer. Contact us at\nPhone : + 1 5168357843\nWhatsApp : +1 7184128918\nMail: help@schengenvisaitinerary.com",
        "explanation": "For unknown or irrelevant queries, should provide contact information for further assistance."
    },
    {
        "query": "Tell me more",
        "expected_response": "Answer with history",
        "explanation": "Should provide additional information based on conversation history or context."
    },
    {
        "query": "price ?",
        "expected_response": "I’m not sure which price you’re referring to. Are you asking about the cost for:\n\n- a flight itinerary\n- a hotel booking\n- travel insurance\n\nor something else?",
        "explanation": "Should seek clarification on which service's price is being asked, listing common options."
    },
    {
        "query": "a flight itinerary",
        "expected_response": "A flight itinerary is a detailed outline of your proposed travel plan to a Schengen or non‑Schengen country. It includes your personal details, flight name, airport IATA codes, booking number (PNR), and scheduled departure and arrival dates and times. It is a dummy or confirmation ticket used for visa processing and cannot be used for actual travel. [Source: Schengen Visa FAQs.docx]",
        "explanation": "Should explain what a flight itinerary is, including its purpose for visa processing."
    },
    {
        "query": "a flight itinerary price",
        "expected_response": "The flight itinerary costs **$40** for a single traveler, which includes a 24‑hour service and covers up to 8 flights. [Source: Schengen Visa FAQs.docx]",
        "explanation": "Should provide the specific price for flight itinerary service."
    },
    {
        "query": "give me all prices",
        "expected_response": "Here are the pricing details we have on file:\n\n- **Flight itinerary**: $40 per traveler (includes a 24‑hour service and covers up to 8 flights) [Source: Schengen Visa FAQs.docx]\n\nIf you’re looking for prices for other services (e.g., hotel booking, travel insurance), let me know and I’ll pull those up for you.",
        "explanation": "Should list available prices, noting limitations and offering to check for more."
    },
    {
        "query": "yes, looking for prices for all other services",
        "expected_response": "I’m sorry, but I don’t have that information. Contact us at\nPhone: +1 516 835 7843\nWhatsApp: +1 718 412 8918\nMail: help@schengenvisaitinerary.com",
        "explanation": "For unavailable information, should apologize and provide contact details."
    },
    {
        "query": "give me all your prices",
        "expected_response": "I’m sorry, but I only have the price for the flight itinerary service on file:\n\n- **Flight itinerary**: $40 per traveler (includes a 24‑hour service and covers up to 8 flights) [Source: Schengen Visa FAQs.docx]\n\nIf you’re looking for prices for other services (e.g., hotel booking, travel insurance), let me know and I’ll check for those.",
        "explanation": "Should list known prices and offer to check for others."
    },
    {
        "query": "all",
        "expected_response": "Here are all the pricing options we have on file:\n\n- **Flight itinerary**: $40 per traveler (includes a 24‑hour service and covers up to 8 flights) [Source: Schengen Visa FAQs.docx]",
        "explanation": "Should provide all available pricing information."
    },
    {
        "query": "What is the price?",
        "expected_response": "Could you let me know which service you’re referring to—flight itinerary, hotel booking, or travel insurance?",
        "explanation": "Should seek clarification on which service's price is needed."
    },
    {
        "query": "hotel booking as well",
        "expected_response": "Could you clarify which service’s price you’re looking for—hotel booking, flight itinerary, travel insurance, or a combined package?",
        "explanation": "Should seek further clarification when multiple services are mentioned."
    },
    {
        "query": "hotel booking",
        "expected_response": "Sorry, I don't have a proper answer. Contact us at\nPhone : + 1 5168357843\nWhatsApp : +1 7184128918\nMail: help@schengenvisaitinerary.com",
        "explanation": "For unavailable information, should provide contact details."
    },
    {
        "query": "what the phone number of tlscontact ?",
        "expected_response": "Which TLScontact office or country do you need the phone number for?",
        "explanation": "Should seek clarification on location for specific contact information."
    },
    {
        "query": "New York, USA",
        "expected_response": "The TLScontact office in New York is reachable at **+1 212‑XXXX‑XXXX**.",
        "explanation": "Should provide the specific phone number for the requested location."
    },
    {
        "query": "what is the address of VFS ?",
        "expected_response": "Could you let me know which VFS Global office or country you’re referring to? That way I can give you the correct address.",
        "explanation": "Should seek clarification on location for address information."
    },
    {
        "query": "what are schengen countries ?",
        "expected_response": "The Schengen Area currently consists of 26 European countries that have abolished border controls between them. These are:\n\n1. Austria\n2. Belgium\n3. Czech Republic\n4. Denmark\n5. Estonia\n6. Finland\n7. France\n8. Germany\n9. Greece\n10. Hungary\n11. Iceland\n12. Italy\n13. Latvia\n14. Liechtenstein\n15. Lithuania\n16. Luxembourg\n17. Malta\n18. Netherlands\n19. Norway\n20. Poland\n21. Portugal\n22. Slovakia\n23. Slovenia\n24. Spain\n25. Sweden\n26. Switzerland\n\nTravelers can move freely between these countries without internal border checks, though they must still comply with visa and entry requirements.",
        "explanation": "Should list all Schengen countries with a brief explanation."
    },
    {
        "query": "flight",
        "expected_response": "The flight itinerary service is priced at **$40** for a single traveler, covering up to 8 flights and a 24‑hour service window. There is no additional fee for adding children under 12 years of age.",
        "explanation": "Should provide pricing details for flight itinerary service."
    },
    {
        "query": "hotel ?",
        "expected_response": "We provide a **Hotel Confirmation** document that verifies your accommodation arrangements during your visit. This serves as proof of your intended stay at a specific hotel or lodging.",
        "explanation": "Should explain what hotel confirmation service entails."
    },
    {
        "query": "hotel cost ?",
        "expected_response": "The cost for a hotel confirmation is **$20** for one hotel. If you need confirmation for additional hotels, each extra hotel adds another **$20**. This base price applies whether you’re booking one traveler or multiple travelers.",
        "explanation": "Should provide specific pricing for hotel confirmation service."
    },
    {
        "query": "can you give me all your prices ?",
        "expected_response": "Here are the current fees for our services:\n\n| Service | Price (USD) | Notes |\n|---------|-------------|-------|\n| Flight itinerary confirmation (up to 8 flights, 24‑hour service window) | **$40** | Includes one traveler; no extra fee for children under 12 years of age. |\n| Hotel confirmation | **$20** | Covers one hotel. Additional hotels add another $20 each. |\n\nThese are the only service fees listed in our current information. If you need pricing for other services, let us know and we’ll check the latest details.",
        "explanation": "Should provide a comprehensive list of all available service prices in a structured format."
    },
    {
        "query": "New york, USA",
        "expected_response": "Could you confirm whether you need a traditional telephone number for the TLScontact office in New York, or would the WhatsApp number +1 718‑412‑8918 be sufficient?",
        "explanation": "Should seek confirmation on the type of contact method needed."
    },
    {
        "query": "Need a traditional telephone number for the TLScontact office ",
        "expected_response": "Sorry, I don’t have a proper answer. Contact us at\nPhone : + 1 5168357843\nWhatsApp : +1 7184128918\nMail: help@schengenvisaitinerary.com",
        "explanation": "For unavailable specific information, should provide general contact details."
    },
    {
        "query": "what is the phone number?",
        "expected_response": "Which phone number are you looking for?",
        "explanation": "Should seek clarification on what specific phone number is needed."
    },
    {
        "query": "USA",
        "expected_response": "Could you clarify whether you need the US country calling code (+1), a general customer‑support number, or a specific business contact in the USA?",
        "explanation": "Should seek further details on the type of phone number required in the USA."
    }
]