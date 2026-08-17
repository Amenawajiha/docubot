from pydantic import BaseModel, Field
from src.api.schemas import ChatRequest

class ChatbotConfig(BaseModel):
    """Per-chatbot configuration."""
    
    workspace_id: str
    chatbot_id: str
    session_id: str
    
    # LLM settings
    llm_provider: str              # 'groq' or 'openai'
    llm_model: str                 # 'mixtral-8x7b', 'gpt-4', etc.
    llm_api_key: str | None = Field(default=None, repr=False)
    
    # RAG settings
    system_prompt: str | None = None
    tone_preset: str | None = None
    memory_mode: str = "buffer"
    context_depth: int = 10
    retrieval_top_k: int = 10
    company_name: str | None = None
    
    @property
    def collection_name(self) -> str:
        """Derive Qdrant collection name from workspace+chatbot pair."""
        return f"workspace_{self.workspace_id}_chatbot_{self.chatbot_id}"
    
    @classmethod
    def from_request(cls, request: ChatRequest) -> "ChatbotConfig":
        """Build config from an incoming ChatRequest."""
        return cls(
            workspace_id=request.workspace_id,
            chatbot_id=request.chatbot_id,
            session_id=request.session_id,
            llm_provider=request.chatbot_config.llm_provider,
            llm_model=request.chatbot_config.llm_model,
            llm_api_key=request.chatbot_config.llm_api_key,
            system_prompt=request.chatbot_config.system_prompt,
            tone_preset=request.chatbot_config.tone_preset,
            company_name=request.chatbot_config.company_name,
        )
