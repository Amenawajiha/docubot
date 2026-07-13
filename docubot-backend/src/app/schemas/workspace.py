import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.validation import make_slug


# ── Workspace requests ────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    # Slug is auto-derived from name if not provided
    slug: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from app.utils.validation import is_valid_slug
        if not is_valid_slug(v):
            raise ValueError(
                "Slug must contain only lowercase letters, numbers, and hyphens."
            )
        return v


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    settings: dict | None = None


# ── Workspace responses ───────────────────────────────────────────────────────

class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    plan_tier: str
    plan_status: str
    monthly_message_limit: int
    chatbot_limit: int
    storage_limit_mb: int
    settings: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceListOut(BaseModel):
    """Lightweight workspace summary for list responses."""
    id: uuid.UUID
    name: str
    slug: str
    plan_tier: str
    role: str           # caller's role in this workspace
    chatbot_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Member requests ───────────────────────────────────────────────────────────

MemberRole = Literal["admin", "editor", "viewer"]


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: MemberRole = "editor"


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole


# ── Member responses ──────────────────────────────────────────────────────────

class MemberOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID | None = None
    role: str
    email: str
    full_name: str | None
    avatar_url: str | None
    invited_at: datetime
    joined_at: datetime | None

    model_config = {"from_attributes": True}


class AcceptInviteRequest(BaseModel):
    token: str