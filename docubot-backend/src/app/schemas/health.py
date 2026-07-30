"""
Pydantic schemas for health and readiness status endpoints.
"""

from pydantic import BaseModel


class ServiceStatuses(BaseModel):
    database: str  # "up" | "down"
    redis: str     # "up" | "down"
    qdrant: str    # "up" | "down"
    minio: str     # "up" | "down"


class HealthReadinessOut(BaseModel):
    status: str    # "ok" | "degraded" | "unhealthy"
    services: ServiceStatuses
