"""
Tests: JWT handler, password hashing, Fernet encryption, token generation.
Pure unit tests — no DB or HTTP needed.
"""

import time
import uuid
import pytest

from app.core.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
)
from app.utils.exceptions import InvalidTokenError, TokenExpiredError
from app.utils.security import (
    decrypt_api_key,
    encrypt_api_key,
    generate_api_key,
    generate_secure_token,
    hash_password,
    verify_password,
    verify_api_key,
)
from app.utils.validation import has_valid_mx


# ── Password hashing ──────────────────────────────────────────────────────────

def test_hash_password_not_plaintext():
    """Stored hash is not the plaintext password."""
    hashed = hash_password("Password1")
    assert hashed != "Password1"
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_password_correct():
    hashed = hash_password("Password1")
    assert verify_password("Password1", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("Password1")
    assert verify_password("WrongPass", hashed) is False


def test_hash_is_unique_per_call():
    """bcrypt generates a fresh salt each time."""
    h1 = hash_password("Password1")
    h2 = hash_password("Password1")
    assert h1 != h2


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_create_and_decode_access_token():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = decode_token(token, "access")
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    uid = uuid.uuid4()
    token, jti = create_refresh_token(uid)
    payload = decode_token(token, "refresh")
    assert payload["sub"] == str(uid)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_refresh_tokens_have_unique_jti():
    uid = uuid.uuid4()
    _, jti1 = create_refresh_token(uid)
    _, jti2 = create_refresh_token(uid)
    assert jti1 != jti2


def test_access_token_rejected_as_refresh():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    with pytest.raises(InvalidTokenError):
        decode_token(token, "refresh")


def test_refresh_token_rejected_as_access():
    uid = uuid.uuid4()
    token, _ = create_refresh_token(uid)
    with pytest.raises(InvalidTokenError):
        decode_token(token, "access")


def test_tampered_token_rejected():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(InvalidTokenError):
        decode_token(tampered, "access")


def test_get_user_id_from_token():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    result = get_user_id_from_token(token, "access")
    assert result == uid


def test_expired_token_raises_token_expired_error():
    """Manually build a token with exp in the past and confirm correct error."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.config import settings

    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # in the past
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(TokenExpiredError):
        decode_token(token, "access")


# ── Fernet encryption ─────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    plain = "sk-openai-my-secret-key-abc123"
    encrypted = encrypt_api_key(plain)
    assert encrypted != plain
    assert decrypt_api_key(encrypted) == plain


def test_encrypted_value_is_different_each_time():
    """Fernet adds a random IV so same input encrypts differently."""
    plain = "sk-test-key"
    e1 = encrypt_api_key(plain)
    e2 = encrypt_api_key(plain)
    assert e1 != e2
    # But both decrypt to same value
    assert decrypt_api_key(e1) == decrypt_api_key(e2) == plain


# ── Secure token generation ────────────────────────────────────────────────────

def test_generate_secure_token_length():
    token = generate_secure_token(64)
    assert len(token) == 64


def test_generate_secure_token_unique():
    t1 = generate_secure_token()
    t2 = generate_secure_token()
    assert t1 != t2


def test_generate_secure_token_url_safe():
    token = generate_secure_token(128)
    import string
    allowed = set(string.ascii_letters + string.digits)
    assert set(token).issubset(allowed)


# ── API key generation ─────────────────────────────────────────────────────────

def test_generate_api_key_format():
    raw, prefix, hashed = generate_api_key()
    assert raw.startswith("db_")
    assert prefix == raw[:12]
    assert hashed.startswith("$2b$")


def test_verify_api_key_correct():
    raw, _, hashed = generate_api_key()
    assert verify_api_key(raw, hashed) is True


def test_verify_api_key_wrong():
    _, _, hashed = generate_api_key()
    assert verify_api_key("db_wrongkey", hashed) is False


# ── MX record validation ──────────────────────────────────────────────────────

def test_has_valid_mx_real_domain():
    """gmail.com definitely has MX records."""
    assert has_valid_mx("test@gmail.com") is True


def test_has_valid_mx_fake_domain():
    """Clearly nonexistent domain returns False."""
    assert has_valid_mx("user@thisdoesnotexist-xyz-abc-999999.io") is False


def test_has_valid_mx_invalid_format():
    """Email without @ returns False without crashing."""
    assert has_valid_mx("notanemail") is False


def test_has_valid_mx_known_providers():
    """Common providers all have MX records."""
    for email in ["u@outlook.com", "u@yahoo.com", "u@hotmail.com"]:
        assert has_valid_mx(email) is True, f"Expected MX for {email}"