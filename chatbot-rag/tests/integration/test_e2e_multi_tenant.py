import os
import time
import requests
import json
import uuid
from src.auth.service import AuthMiddleware
from dotenv import load_dotenv

load_dotenv()

# Configuration parameters
CHATBOT_RAG_API_URL = "http://127.0.0.1:8000/api/chat"
INTERNAL_API_KEY = "local_development_internal_api_key"

# Generate a mock config payload
# This mimics what docubot-backend generates for multi-tenant isolation
config_payload = {
    "company_name": "Test Company Inc.",
    "system_prompt": "Answer accurately and politely.",
    "tone_preset": "professional",
    "llm_provider": "groq",
    "llm_model": "openai/gpt-oss-20b",
    "llm_api_key": os.getenv("GROQ_API_KEY", "")
}

# Generate valid JWT
auth_middleware = AuthMiddleware()
bearer_token = auth_middleware.generate_jwt(user_id=1)

headers = {
    "Content-Type": "application/json",
    "X-Internal-API-Key": INTERNAL_API_KEY,
    "Authorization": f"Bearer {bearer_token}"
}

payload = {
    "workspace_id": "test_workspace_001",
    "chatbot_id": "test_chatbot_001",
    "session_id": str(uuid.uuid4()),
    "message": "What is your company's name and what is a Schengen visa?",
    "history": [],
    "chatbot_config": config_payload
}

def run_test():
    print(f"Testing Chat API at {CHATBOT_RAG_API_URL}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(CHATBOT_RAG_API_URL, headers=headers, json=payload)
        elapsed = time.time() - start_time
        
        print(f"\nResponse Code: {response.status_code} ({elapsed:.2f}s)")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success!")
            print(f"Response: {result.get('response')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"Clarification Q: {result.get('clarification_question')}")
            print(f"Sources: {result.get('sources')}")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the chatbot-rag FastAPI server running on port 8000?")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    run_test()
