"""Guards for the deployment and account-takeover fixes."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.api.v1.endpoints.auth import assess_reset_token, hash_password, password_is_hashed, verify_password
from app.core.config import Settings, validate_for_runtime
from app.core.sessions import SessionStore, SessionUnavailable


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_bcrypt_mismatch_does_not_fall_through_to_plaintext():
    stored = hash_password("correct-horse")
    assert password_is_hashed(stored)
    assert verify_password("correct-horse", stored) is True
    assert verify_password(stored, stored) is False
    assert verify_password("correct-horse", "correct-horse") is True
    assert verify_password("other", "correct-horse") is False


def test_reset_token_requires_an_exact_unexpired_match():
    created = datetime.utcnow() - timedelta(minutes=5)
    assert assess_reset_token("abc", "abc", created) == "ok"
    assert assess_reset_token("abc", "demo-reset-token", created) == "invalid"
    assert assess_reset_token(None, "abc", created) == "invalid"
    expired = datetime.utcnow() - timedelta(minutes=61)
    assert assess_reset_token("abc", "abc", expired) == "expired"
    aware = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert assess_reset_token("abc", "abc", aware) == "ok"


def test_startup_rejects_the_leaked_database_password():
    settings = Settings(
        ENVIRONMENT="development",
        SECRET_KEY="a" * 32,
        DATABASE_URL="mysql+aiomysql://mary_admin:my_admin_pass_01@127.0.0.1:3306/mary",
    )
    with pytest.raises(RuntimeError, match="placeholder"):
        validate_for_runtime(settings)


def test_production_settings_reject_a_short_secret():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="too-short",
        DATABASE_URL="mysql+aiomysql://user:real-password@db.example:25060/mary",
        REDIS_URL="redis://:long-password@redis:6379/0",
        SESSION_MEMORY_FALLBACK=False,
        AUTO_CREATE_TABLES=False,
        CORS_ORIGINS="https://app.example.com",
        PUBLIC_BASE_URL="https://app.example.com",
        SMTP_USER="mail@example.com",
        SMTP_PASSWORD="mailbox-password",
        ALLOWED_HOSTS="app.example.com",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_for_runtime(settings)


def test_production_accepts_an_explicit_configuration():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 32,
        DATABASE_URL="mysql+aiomysql://user:real-password@db.example:25060/mary",
        REDIS_URL="redis://:long-password@redis:6379/0",
        SESSION_MEMORY_FALLBACK=False,
        AUTO_CREATE_TABLES=False,
        CORS_ORIGINS="https://app.example.com",
        PUBLIC_BASE_URL="https://app.example.com",
        SMTP_USER="mail@example.com",
        SMTP_PASSWORD="mailbox-password",
        ALLOWED_HOSTS="app.example.com",
    )
    validate_for_runtime(settings)


def test_session_store_refuses_memory_when_fallback_is_disabled():
    async def scenario():
        store = SessionStore(connect_redis=False, allow_memory_fallback=False)
        with pytest.raises(SessionUnavailable):
            await store.put("mary_tok_x", {"user_id": 1, "user": {}, "created_at": datetime.utcnow()})

    asyncio.run(scenario())


def test_tracked_runtime_files_do_not_embed_the_old_mailbox_secrets():
    banned = ("StmarysServiceAccount", "HernU-0412", "supersecretjwtkey_change_in_production", "my_admin_pass_01")
    paths = [
        ROOT / "app" / "api" / "v1" / "endpoints" / "auth.py",
        REPO / "docker-compose.yml",
        REPO / "docker-compose.prod.yml",
        REPO / ".env.example",
        REPO / ".env.production.example",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for secret in banned:
            assert secret not in text, f"{secret} is still in {path.name}"
