"""Pydantic schemas — Phase 6 Analytics."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AnalyticsEventOut(BaseModel):
    id: uuid.UUID
    chatbot_id: uuid.UUID
    workspace_id: uuid.UUID
    session_id: uuid.UUID | None
    event_type: str
    event_data: dict[str, Any]
    confidence_score: Decimal | None
    tokens_used: int
    response_time_ms: int | None
    created_at: datetime
    model_config = {"from_attributes": True}


class DailyMetricOut(BaseModel):
    date: date
    chatbot_id: uuid.UUID
    total_sessions: int
    total_messages: int
    unique_users: int
    avg_confidence: Decimal | None
    avg_response_time_ms: int | None
    total_tokens: int
    clarification_rate: Decimal | None
    resolution_rate: Decimal | None
    total_cost_usd: Decimal
    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    """Aggregated stats for a date range — used by dashboard cards."""
    workspace_id: uuid.UUID
    chatbot_id: uuid.UUID | None
    period_start: date
    period_end: date
    total_sessions: int
    total_messages: int
    unique_users: int
    avg_confidence: float | None
    avg_response_time_ms: int | None
    total_tokens: int
    total_cost_usd: float
    clarification_rate: float | None
    resolution_rate: float | None


class TopQuestion(BaseModel):
    content: str
    count: int
    avg_confidence: float | None


class AnalyticsDashboard(BaseModel):
    """Full dashboard payload for the frontend."""
    summary: AnalyticsSummary
    daily_metrics: list[DailyMetricOut]
    top_questions: list[TopQuestion]