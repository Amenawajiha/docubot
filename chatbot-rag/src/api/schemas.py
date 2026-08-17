from pydantic import BaseModel, Field

class ChatbotConfigPayload(BaseModel):
    """Payload from docubot-backend containing per-chatbot settings."""
    llm_provider: str
    llm_model: str
    llm_api_key: str | None = Field(default=None, repr=False)
    system_prompt: str | None = None
    tone_preset: str | None = None
    company_name: str | None = None

class ChatRequest(BaseModel):
    workspace_id: str
    chatbot_id: str
    session_id: str
    message: str
    history: list[dict]                  # [{"role": "user", "content": "..."}]
    chatbot_config: ChatbotConfigPayload # LLM/RAG settings from docubot-backend

class ChatResponse(BaseModel):
    response: str
    confidence: float
    sources: list[dict]
    clarification_question: str | None
    tokens: dict                         # {"input": N, "output": M}
    execution_time_ms: int
    was_summarized: bool = False
    summarized_count: int = 0
    summary_text: str | None = None
