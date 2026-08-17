import re
import html
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional, Dict, Any
from datetime import datetime


class Message(BaseModel):
    """Represents a message, including content, role, timestamp, user ID, and optional metadata."""

    content: str

    role: Literal["user", "assistant"]

    timestamp: datetime
    user_id: int

    metadata: Optional[dict] = {}


class ConfidenceResult(BaseModel):
    """Represents a confidence result, including retrieval confidence, LLM confidence, overall confidence, and confidence breakdown."""

    retrieval_confidence: float
    llm_confidence: float
    overall_confidence: float
    is_confident: bool
    confidence_breakdown: dict


class ScoringWeights(BaseModel):
    """Represents the weights for scoring retrieval and LLM responses."""

    retrieval_weight: float = 0.4
    llm_weight: float = 0.6


class RetrievalResult(BaseModel):
    """Represents a retrieval result, including content, metadata, and relevance score."""

    content: str
    metadata: dict
    relevance_score: float


class User(BaseModel):
    id: str
    email: Optional[str] = None
    user_type: str = "guest"
    created_at: datetime
    last_active: datetime

class IncomingMessagePayload(BaseModel):
    """Validated payload for incoming messages from clients."""
    
    content: str = Field(..., min_length=1, max_length=10000)
    timestamp: Optional[str] = None  # Will be validated and potentially overwritten
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize content to prevent XSS and injection attacks."""
        # HTML escape the content
        sanitized = html.escape(v.strip())
        
        # Remove any null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Limit consecutive whitespace
        sanitized = re.sub(r'\s{10,}', ' ' * 10, sanitized)
        
        return sanitized
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and sanitize metadata."""
        if v is None:
            return {}
        
        # Whitelist allowed metadata keys
        allowed_keys = {'interaction_type', 'form_data'}
        allowed_interaction_types = {'button_click', 'form_submission', 'message', 'bot_response'}
        
        sanitized = {}
        
        for key, value in v.items():
            if key not in allowed_keys:
                continue  # Skip unknown keys
            
            if key == 'interaction_type':
                if value in allowed_interaction_types:
                    sanitized[key] = value
                else:
                    sanitized[key] = 'message'  # Default to safe value
            
            elif key == 'form_data':
                # Sanitize form data values
                if isinstance(value, dict):
                    sanitized[key] = {
                        str(k)[:100]: html.escape(str(val))[:1000] 
                        for k, val in value.items() 
                        if len(value) <= 50  # Limit number of form fields
                    }
        
        return sanitized


class ValidatedStoredMessage(BaseModel):
    """Server-side validated message ready for storage."""
    
    content: str
    role: Literal["user"]  # Client can ONLY submit user messages
    timestamp: datetime
    user_id: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_client_payload(
        cls, 
        payload: IncomingMessagePayload, 
        user_id: int
    ) -> "ValidatedStoredMessage":
        """Create a validated message from client payload.
        
        Server controls: role (always 'user') and timestamp (server time).
        """
        return cls(
            content=payload.content,
            role="user",  # Force role to be user - clients cannot send as assistant
            timestamp=datetime.utcnow(),  # Use server timestamp
            user_id=user_id,
            metadata=payload.metadata
        )


class WebSocketMessageRequest(BaseModel):
    """Validates the structure of incoming WebSocket messages."""
    
    type: Literal["query", "store_message"] = "query"
    query: Optional[str] = Field(None, max_length=5000)
    message: Optional[IncomingMessagePayload] = None
    
    @model_validator(mode='after')
    def validate_message_type(self) -> "WebSocketMessageRequest":
        """Ensure proper fields are present based on message type."""
        if self.type == "query" and not self.query:
            raise ValueError("Query cannot be empty for query type messages")
        if self.type == "store_message" and not self.message:
            raise ValueError("Message payload required for store_message type")
        return self
    
    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return html.escape(v.strip())