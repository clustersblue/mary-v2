"""Bearer session registry.

Login issues an opaque mary_tok_ token. The record lives in Redis when
REDIS_URL is reachable, so any worker and any restart can validate it.
If Redis is down, the same process keeps the record in memory.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SESSION_PREFIX = "mary:session:"
_RETRY_SECONDS = 5


class SessionUnavailable(RuntimeError):
    """Redis is required and did not accept the session write."""


def session_is_expired(created_at: Optional[datetime]) -> bool:
    if not created_at:
        return False
    lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return datetime.utcnow() - created_at > lifetime


class SessionStore:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        connect_redis: bool = True,
        allow_memory_fallback: Optional[bool] = None,
    ) -> None:
        self._redis_url = settings.REDIS_URL if redis_url is None else redis_url
        self._connect_redis = connect_redis
        if allow_memory_fallback is None:
            allow_memory_fallback = settings.SESSION_MEMORY_FALLBACK if connect_redis else True
        self._allow_memory_fallback = allow_memory_fallback
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._local_only: set[str] = set()
        self._redis = None
        self._retry_after = 0.0

    def _key(self, token: str) -> str:
        return f"{SESSION_PREFIX}{token}"

    async def _client(self):
        if self._redis is not None:
            return self._redis
        if not self._connect_redis:
            return None
        now = time.monotonic()
        if now < self._retry_after:
            return None
        try:
            from redis.asyncio import Redis

            client = Redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=1.0,
            )
            await client.ping()
            self._redis = client
            logger.info("Session store connected to Redis")
            return client
        except Exception as exc:
            self._retry_after = now + _RETRY_SECONDS
            logger.warning("Redis session store unavailable, using in-memory sessions: %s", exc)
            return None

    def _remember(self, token: str, user: Any, user_id: Any, created_at: datetime) -> Dict[str, Any]:
        record = {"user": user, "user_id": user_id, "created_at": created_at}
        self._memory[token] = record
        return record

    def _decode(self, raw: str) -> Dict[str, Any]:
        data = json.loads(raw)
        created = data.get("created_at")
        if isinstance(created, str):
            data["created_at"] = datetime.fromisoformat(created)
        return data

    async def get(self, token: str) -> Optional[Dict[str, Any]]:
        client = await self._client()
        if client is not None:
            try:
                raw = await client.get(self._key(token))
                if not raw:
                    if token in self._local_only:
                        return self._memory.get(token)
                    self._memory.pop(token, None)
                    return None
                decoded = self._decode(raw)
                self._local_only.discard(token)
                self._memory[token] = decoded
                return decoded
            except Exception as exc:
                logger.warning("Redis session read failed: %s", exc)
                self._redis = None
                self._retry_after = time.monotonic() + _RETRY_SECONDS
        if not self._allow_memory_fallback:
            return None
        return self._memory.get(token)

    async def put(self, token: str, data: Dict[str, Any]) -> None:
        created_at = data.get("created_at") or datetime.utcnow()
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        record = self._remember(token, data.get("user"), data.get("user_id"), created_at)
        client = await self._client()
        if client is None:
            if not self._allow_memory_fallback:
                self._memory.pop(token, None)
                raise SessionUnavailable("Session store is unavailable")
            self._local_only.add(token)
            return
        payload = {
            "user": record["user"],
            "user_id": record["user_id"],
            "created_at": created_at.isoformat(),
        }
        ttl = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        try:
            await client.set(self._key(token), json.dumps(payload), ex=ttl)
            self._local_only.discard(token)
        except Exception as exc:
            logger.warning("Redis session write failed: %s", exc)
            self._redis = None
            self._retry_after = time.monotonic() + _RETRY_SECONDS
            if not self._allow_memory_fallback:
                self._memory.pop(token, None)
                raise SessionUnavailable("Session store is unavailable") from exc
            self._local_only.add(token)

    async def delete(self, token: str) -> None:
        self._memory.pop(token, None)
        self._local_only.discard(token)
        client = await self._client()
        if client is None:
            return
        try:
            await client.delete(self._key(token))
        except Exception as exc:
            logger.warning("Redis session delete failed: %s", exc)
            self._redis = None
            self._retry_after = time.monotonic() + _RETRY_SECONDS

    async def update_user(self, token: str, user_data: Dict[str, Any]) -> None:
        current = await self.get(token)
        if not current:
            return
        created_at = current.get("created_at") or datetime.utcnow()
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        self._remember(token, user_data, current.get("user_id"), created_at)
        client = self._redis
        if client is None:
            if not self._allow_memory_fallback:
                raise SessionUnavailable("Session store is unavailable")
            return
        payload = {
            "user": user_data,
            "user_id": current.get("user_id"),
            "created_at": created_at.isoformat(),
        }
        try:
            remaining = await client.ttl(self._key(token))
            ttl = remaining if remaining and remaining > 0 else int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            await client.set(self._key(token), json.dumps(payload), ex=ttl)
            self._local_only.discard(token)
        except Exception as exc:
            logger.warning("Redis session update failed: %s", exc)
            self._redis = None
            self._retry_after = time.monotonic() + _RETRY_SECONDS
            if not self._allow_memory_fallback:
                raise SessionUnavailable("Session store is unavailable") from exc
            self._local_only.add(token)

    async def ready(self) -> bool:
        if not self._connect_redis:
            return True
        client = await self._client()
        if client is not None:
            return True
        return self._allow_memory_fallback


session_store = SessionStore()
