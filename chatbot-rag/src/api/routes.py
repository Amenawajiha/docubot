import os
from fastapi import APIRouter, Header, HTTPException

from src.api.schemas import ChatRequest, ChatResponse
from src.config.chatbot_config import ChatbotConfig
from src.engine.chat_engine_factory import ChatEngineFactory
from src.auth.service import AuthMiddleware
from src.utils.log_helper import logger

def _validate_internal_key(key: str) -> None:
    """Validate the internal API key shared between docubot-backend and chatbot-rag."""
    expected = os.environ.get("INTERNAL_API_KEY")
    if not expected:
        logger.warning("INTERNAL_API_KEY not set — /api/chat endpoint is unsecured!")
        return
    if key != expected:
        raise HTTPException(status_code=401, detail="Invalid internal API key")

api_router = APIRouter(prefix="/api")

@api_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    x_internal_api_key: str = Header(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Stateless multi-tenant chat endpoint called by docubot-backend per user message."""
    # 1. Validate internal API key
    _validate_internal_key(x_internal_api_key)
    
    # 2. Extract user_id from JWT or fallback to session_id
    uid = request.session_id
    if authorization:
        bearer_token = authorization.removeprefix("Bearer ").strip()
        user_id_data = AuthMiddleware().get_current_user(bearer_token)
        if isinstance(user_id_data, dict) and "error" in user_id_data:
            logger.warning("Invalid token provided, falling back to session_id")
        else:
            uid = user_id_data.get("user_id") if isinstance(user_id_data, dict) else str(user_id_data)
    
    # 3. Build ChatbotConfig from request payload
    config = ChatbotConfig.from_request(request)
    
    # 4. Get or create tenant-specific engine
    engine = ChatEngineFactory.get_or_create(config)
    
    # 5. Run RAG pipeline
    result = await engine.process_message(
        message=request.message,
        history=request.history,
        user_id=uid,
    )
    
    # 6. Return structured response
    return ChatResponse(
        response=result.get("response", ""),
        confidence=result.get("confidence", 1.0),
        sources=result.get("sources", []),
        clarification_question=result.get("clarification_question"),
        tokens=result.get("tokens", {"input": 0, "output": 0}),
        execution_time_ms=result.get("execution_time_ms", 0),
    )
