import secrets
import string
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
# Using Argon2 instead of bcrypt to avoid 72-byte password length limitations
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── Fernet (symmetric encryption for custom LLM API keys) ────────────────────

_fernet = Fernet(settings.fernet_key.encode())


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt a plaintext API key for storage."""
    return _fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a stored API key for use at runtime."""
    return _fernet.decrypt(encrypted_key.encode()).decode()


# ── Secure token helpers ──────────────────────────────────────────────────────

def generate_secure_token(length: int = 64) -> str:
    """Generate a URL-safe random token (used for email verification / resets)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def token_expiry(*, hours: int = 0, days: int = 0) -> datetime:
    """Return a UTC-aware expiry timestamp."""
    return datetime.now(timezone.utc) + timedelta(hours=hours, days=days)


# ── API key generation (workspace API keys) ───────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a workspace API key.

    Returns:
        (raw_key, key_prefix, key_hash)
        - raw_key  : shown once to the user (e.g. "db_xxxx...")
        - key_prefix: stored in plain text for lookup (first 12 chars)
        - key_hash : bcrypt hash stored in the DB
    """
    raw = "db_" + secrets.token_urlsafe(40)
    prefix = raw[:12]
    hashed = _pwd_context.hash(raw)
    return raw, prefix, hashed


def verify_api_key(raw: str, hashed: str) -> bool:
    return _pwd_context.verify(raw, hashed)