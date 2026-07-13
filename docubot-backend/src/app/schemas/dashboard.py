"""
Pydantic schemas for the Workspace Overview Dashboard.

Deliberately narrow — this layer composes domain data for the frontend
overview page only.  Deep analytics live in schemas/analytics.py.
"""

from pydantic import BaseModel, Field


class DashboardMetricsOut(BaseModel):
    """
    High-level numbers shown in the four stat cards on the overview page.

    active_bots         — chatbots with deployment_status == "published"
    total_conversations — all-time session count across the workspace
    satisfaction_rate   — workspace-wide avg confidence score (0–1), None
                          when no conversations have been recorded yet
    total_documents     — documents with upload_status == "completed" across
                          all chatbots in this workspace
    """
    active_bots: int
    total_conversations: int
    satisfaction_rate: float | None
    total_documents: int


class DashboardChecklistOut(BaseModel):
    """
    Boolean flags that drive the "Getting Started" checklist widget.

    has_chatbot     — at least one chatbot exists in this workspace
    has_documents   — at least one completed document exists workspace-wide
    has_deployments — at least one active deployment channel exists
    has_conversations — at least one chat session has been started
    """
    has_chatbot: bool
    has_documents: bool
    has_deployments: bool
    has_conversations: bool


class DashboardOut(BaseModel):
    """Root payload for GET /workspaces/{id}/dashboard."""
    metrics: DashboardMetricsOut
    checklist: DashboardChecklistOut
    setup_progress_percent: int = Field(
        ge=0, le=100,
        description=(
            "Percentage of the Getting Started checklist that is complete. "
            "Computed as (completed_steps / total_steps) * 100, rounded to "
            "the nearest 25."
        ),
    )