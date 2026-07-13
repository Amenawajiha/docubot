"""Pydantic schemas — Phase 8 Billing."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PlanOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    price_monthly_usd: Decimal
    price_yearly_usd: Decimal | None
    chatbot_limit: int
    monthly_message_limit: int
    storage_limit_mb: int
    team_member_limit: int
    features: list[str]
    is_active: bool
    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str
    status: str
    billing_cycle: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_ends_at: datetime | None
    canceled_at: datetime | None
    model_config = {"from_attributes": True}


class ChangePlanRequest(BaseModel):
    plan_id: uuid.UUID
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")


class LineItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: int
    unit_price: Decimal
    amount_usd: Decimal
    item_type: str
    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    invoice_number: str
    status: str
    currency: str
    subtotal_usd: Decimal
    tax_usd: Decimal
    total_usd: Decimal
    period_start: date
    period_end: date
    paid_at: datetime | None
    due_at: datetime | None
    created_at: datetime
    line_items: list[LineItemOut] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class UsageSummaryOut(BaseModel):
    """Current billing period usage vs plan limits."""
    workspace_id: uuid.UUID
    plan_name: str
    billing_cycle: str
    period_start: date | None
    period_end: date | None
    messages_used: int
    messages_limit: int
    messages_pct: float
    chatbots_used: int
    chatbots_limit: int
    storage_used_mb: float
    storage_limit_mb: int
    tokens_used: int
    estimated_cost_usd: float