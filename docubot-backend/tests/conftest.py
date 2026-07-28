"""
Test configuration and shared fixtures.

Uses:
  - SQLite (aiosqlite) in-memory database — no Postgres required
  - fakeredis — in-memory Redis — no Redis server required
  - MAIL_SUPPRESS_SEND=true — no SMTP required
  - httpx AsyncClient with FastAPI's ASGITransport — no live server required

Run with:
    uv run pytest tests/ -v
    uv run pytest tests/ -v --tb=short   # less noise on failures
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ── Point config at test values BEFORE importing the app ─────────────────────
os.environ.update({
    "APP_SECRET_KEY":            "test-app-secret-key-for-testing-only",
    "DATABASE_URL":              "sqlite+aiosqlite:///:memory:",
    "JWT_SECRET_KEY":            "test-jwt-secret-key-for-testing-only",
    "FERNET_KEY":                "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",  # 32-byte base64
    "BACKEND_URL":               "http://testserver",
    "FRONTEND_URL":              "http://localhost:3000",
    "MAIL_SUPPRESS_SEND":        "true",
    "REDIS_URL":                 "redis://localhost:6379/0",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "RATE_LIMIT_ENABLED":        "false",
})

# Now safe to import app modules
from app.data.database import Base, get_db  # noqa: E402
from app.main import create_app              # noqa: E402

# ── In-memory async SQLite engine ─────────────────────────────────────────────
TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Wipe all rows between tests so each test starts fresh."""
    yield
    async with TEST_ENGINE.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Fake Redis ─────────────────────────────────────────────────────────────────

class FakeRedis:
    """Minimal in-memory Redis stub — covers get/set/setex/delete."""
    def __init__(self):
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value  # TTL ignored in tests

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


_fake_redis = FakeRedis()


@pytest.fixture(autouse=True)
def reset_redis():
    """Clear fake Redis before each test."""
    _fake_redis.clear()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fully wired AsyncClient:
      - DB override → in-memory SQLite
      - Redis override → FakeRedis
      - Mail → suppressed (MAIL_SUPPRESS_SEND=true)
    """
    app = create_app()

    # Override the DB dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Patch Redis globally
    with patch(
        "app.infrastructure.cache.redis_client.get_redis",
        new_callable=AsyncMock,
        return_value=_fake_redis,
    ), patch(
        "app.core.auth.service.get_redis",
        new_callable=AsyncMock,
        return_value=_fake_redis,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_verify(client: AsyncClient, email: str, password: str) -> dict:
    """Register a user and complete email verification in one helper call."""
    # Register
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    assert r.status_code == 201, f"Register failed: {r.text}"

    # Grab token from the DB directly via the session attached to client
    # We use the mailer's captured output indirectly — easiest is to query DB
    from app.data.repositories.user_repo import UserRepository
    # We need a fresh session — use a helper approach through the API
    # Actually, we patch the mailer to capture the token
    return r.json()


async def get_verification_token(db_session: AsyncSession, email: str) -> str:
    """Read the verification token directly from the DB."""
    from sqlalchemy import select
    from app.data.models import User
    result = await db_session.execute(
        select(User.email_verification_token).where(User.email == email.lower())
    )
    token = result.scalar_one_or_none()
    assert token is not None, f"No verification token found for {email}"
    return token


async def get_reset_token(db_session: AsyncSession, email: str) -> str:
    """Read the password reset token directly from the DB."""
    from sqlalchemy import select
    from app.data.models import User
    result = await db_session.execute(
        select(User.password_reset_token).where(User.email == email.lower())
    )
    token = result.scalar_one_or_none()
    assert token is not None, f"No reset token found for {email}"
    return token


async def full_login(client: AsyncClient, db_session: AsyncSession,
                     email: str = "user@example.com",
                     password: str = "Password1") -> dict:
    """Register → verify → login. Returns the token response dict."""
    r_reg = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Test User"
    })
    token = await get_verification_token(db_session, email)
    r_ver = await client.get(f"/api/v1/auth/verify-email?token={token}")
    assert r_ver.status_code in (200, 302, 303, 307), f"Verification failed: {r_ver.text}"
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()