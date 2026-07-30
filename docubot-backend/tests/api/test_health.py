"""
Tests for health & readiness endpoints.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_all_ok(client: AsyncClient) -> None:
    with patch("app.api.health._check_db", return_value=True), \
         patch("app.api.health._check_qdrant", return_value=True), \
         patch("app.api.health._check_redis", return_value=True), \
         patch("app.api.health._check_minio", return_value=True):
        response = await client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["services"] == {
            "database": "up",
            "redis": "up",
            "qdrant": "up",
            "minio": "up",
        }


@pytest.mark.asyncio
async def test_readiness_optional_service_down(client: AsyncClient) -> None:
    # Redis down, MinIO down, DB and Qdrant up -> HTTP 200 (degraded)
    with patch("app.api.health._check_db", return_value=True), \
         patch("app.api.health._check_qdrant", return_value=True), \
         patch("app.api.health._check_redis", return_value=False), \
         patch("app.api.health._check_minio", return_value=True):
        response = await client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["redis"] == "down"
        assert data["services"]["database"] == "up"


@pytest.mark.asyncio
async def test_readiness_core_service_down(client: AsyncClient) -> None:
    # Core service DB down -> HTTP 503 (unhealthy)
    with patch("app.api.health._check_db", return_value=False), \
         patch("app.api.health._check_qdrant", return_value=True), \
         patch("app.api.health._check_redis", return_value=True), \
         patch("app.api.health._check_minio", return_value=True):
        response = await client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["database"] == "down"


@pytest.mark.asyncio
async def test_readiness_qdrant_down(client: AsyncClient) -> None:
    # Core service Qdrant down -> HTTP 503 (unhealthy)
    with patch("app.api.health._check_db", return_value=True), \
         patch("app.api.health._check_qdrant", return_value=False), \
         patch("app.api.health._check_redis", return_value=True), \
         patch("app.api.health._check_minio", return_value=True):
        response = await client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["qdrant"] == "down"
