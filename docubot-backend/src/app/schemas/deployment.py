"""Pydantic schemas — Phase 7 Deployment channels."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WidgetChannelConfig(BaseModel):
    """Config specific to an embeddable widget channel."""
    allowed_domains: list[str] = Field(default_factory=list)
    theme: str = "light"                   # light | dark | auto
    position: str = "bottom-right"         # bottom-right | bottom-left
    z_index: int = 9999


class ApiChannelConfig(BaseModel):
    """Config specific to a direct REST API channel."""
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    allowed_origins: list[str] = Field(default_factory=list)


class CreateChannelRequest(BaseModel):
    channel_type: str = Field(pattern="^(widget|api)$")
    channel_name: str = Field(min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    allowed_domains: list[str] = Field(default_factory=list)


class UpdateChannelRequest(BaseModel):
    channel_name: str | None = Field(default=None, max_length=255)
    config: dict[str, Any] | None = None
    allowed_domains: list[str] | None = None
    is_active: bool | None = None


class ChannelOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    chatbot_id: uuid.UUID
    channel_type: str
    channel_name: str
    config: dict[str, Any]
    allowed_domains: list[str]
    is_active: bool
    has_api_key: bool           # True if api_key_hash is set (key never returned)
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class WidgetEmbedOut(BaseModel):
    """HTML snippet + JS snippet for embedding the chat widget."""
    chatbot_id: uuid.UUID
    channel_id: uuid.UUID
    widget_url: str
    embed_script: str           # <script> tag to paste into <head>
    embed_div: str              # <div> placeholder to paste in <body>