import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.validation import is_valid_hex_color


LlmProvider  = Literal["openai", "groq", "ollama", "anthropic"]
TonePreset   = Literal["friendly", "professional", "concise", "custom"]
WidgetStyle  = Literal["bubble", "fullscreen", "inline"]
MemoryMode   = Literal["persistent", "none"]
AuthMode     = Literal["public", "passcode", "authenticated"]
DeployStatus = Literal["draft", "published", "paused", "archived"]


# ── Chatbot requests ──────────────────────────────────────────────────────────

class ChatbotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    # Identity
    brand_color: str = Field(default="#3B82F6", max_length=7)

    # LLM
    llm_provider: LlmProvider = "groq"
    llm_model: str = Field(default="llama-3.3-70b-versatile", max_length=100)
    custom_api_key: str | None = Field(default=None, max_length=500)

    # Personality
    tone_preset: TonePreset = "friendly"
    custom_system_prompt: str | None = None

    # Language
    default_language: str = Field(default="auto", max_length=10)
    fallback_language: str = Field(default="en", max_length=10)

    # Widget
    widget_style: WidgetStyle = "bubble"
    welcome_message: str = Field(
        default="Hi! How can I help you today?", max_length=1000
    )
    input_placeholder: str = Field(
        default="Type your question here...", max_length=200
    )

    # Memory
    memory_mode: MemoryMode = "persistent"

    # Access
    auth_mode: AuthMode = "public"
    passcode: str | None = Field(default=None, min_length=4, max_length=128)

    @field_validator("brand_color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not is_valid_hex_color(v):
            raise ValueError("brand_color must be a valid hex color (e.g. #3B82F6).")
        return v


class ChatbotUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    brand_color: str | None = Field(default=None, max_length=7)
    deployment_status: DeployStatus | None = None
    is_active: bool | None = None
    llm_provider: LlmProvider | None = None
    llm_model: str | None = Field(default=None, max_length=100)
    custom_api_key: str | None = None
    tone_preset: TonePreset | None = None
    custom_system_prompt: str | None = None
    default_language: str | None = Field(default=None, max_length=10)
    fallback_language: str | None = Field(default=None, max_length=10)
    widget_style: WidgetStyle | None = None
    welcome_message: str | None = Field(default=None, max_length=1000)
    input_placeholder: str | None = Field(default=None, max_length=200)
    memory_mode: MemoryMode | None = None
    auth_mode: AuthMode | None = None
    passcode: str | None = Field(default=None, min_length=4, max_length=128)

    @field_validator("brand_color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_hex_color(v):
            raise ValueError("brand_color must be a valid hex color (e.g. #3B82F6).")
        return v


# ── Chatbot responses ─────────────────────────────────────────────────────────

class ChatbotOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    brand_color: str
    llm_provider: str
    llm_model: str
    has_custom_api_key: bool        # true/false — never expose the key itself
    custom_api_key_masked: str | None = None
    tone_preset: str
    custom_system_prompt: str | None
    default_language: str
    fallback_language: str
    widget_style: str
    welcome_message: str
    input_placeholder: str
    memory_mode: str
    auth_mode: str
    is_active: bool
    deployment_status: str
    total_messages: int
    total_conversations: int
    resolution_rate: Decimal | None
    avg_response_time_ms: int | None
    avg_confidence_score: Decimal | None
    created_at: datetime
    updated_at: datetime
    last_trained_at: datetime | None
    last_deployed_at: datetime | None

    model_config = {"from_attributes": True}


class ChatbotListOut(BaseModel):
    """Lightweight chatbot summary for list responses."""
    id: uuid.UUID
    name: str
    brand_color: str
    llm_provider: str
    llm_model: str
    custom_system_prompt: str | None
    is_active: bool
    deployment_status: str
    total_messages: int
    total_conversations: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotDeployResponse(BaseModel):
    id: uuid.UUID
    deployment_status: str
    is_active: bool
    last_deployed_at: datetime | None
    embed_snippet: str      # JS snippet the user pastes into their site

    model_config = {"from_attributes": True}