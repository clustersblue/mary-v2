"""Opaque login sessions survive a lookup and keep their original expiry."""

import asyncio
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("httpx", types.ModuleType("httpx"))

from app.core.config import settings
from app.core.sessions import SessionStore, session_is_expired


def test_put_get_delete_round_trip():
    async def scenario():
        store = SessionStore(connect_redis=False)
        created = datetime.utcnow()
        await store.put("mary_tok_abc", {"user": {"id": 7, "username": "ada"}, "user_id": 7, "created_at": created})

        loaded = await store.get("mary_tok_abc")
        assert loaded["user_id"] == 7
        assert loaded["user"]["username"] == "ada"
        assert loaded["created_at"] == created

        await store.update_user("mary_tok_abc", {"id": 7, "username": "ada updated"})
        updated = await store.get("mary_tok_abc")
        assert updated["user"]["username"] == "ada updated"
        assert updated["created_at"] == created

        await store.delete("mary_tok_abc")
        assert await store.get("mary_tok_abc") is None

    asyncio.run(scenario())


def test_redis_miss_drops_a_shared_session_and_keeps_a_local_one():
    class EmptyRedis:
        async def get(self, key):
            return None

    async def scenario():
        store = SessionStore(connect_redis=False)
        created = datetime.utcnow()
        await store.put("mary_tok_local", {"user": {"id": 7}, "user_id": 7, "created_at": created})
        await store.put("mary_tok_shared", {"user": {"id": 8}, "user_id": 8, "created_at": created})
        store._local_only.discard("mary_tok_shared")
        store._redis = EmptyRedis()
        assert (await store.get("mary_tok_local"))["user_id"] == 7
        assert await store.get("mary_tok_shared") is None

    asyncio.run(scenario())


def test_session_expiry_uses_the_configured_lifetime():
    fresh = datetime.utcnow() - timedelta(minutes=5)
    stale = datetime.utcnow() - timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES + 1)
    assert session_is_expired(fresh) is False
    assert session_is_expired(stale) is True
    assert session_is_expired(None) is False
