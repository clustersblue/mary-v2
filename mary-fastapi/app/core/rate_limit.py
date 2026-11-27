"""Small in-process limiter for login and password reset.

Nginx applies the same limits at the edge. This covers a request that
reaches Uvicorn directly, and it follows the account name as well as the
address so one office NAT does not share a single bucket with every carer.
"""

import ipaddress
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_hits: dict[str, list[float]] = defaultdict(list)


def client_address(request: Request) -> str:
    peer = request.client.host if request.client else ""
    if _is_proxy(peer):
        real = (request.headers.get("x-real-ip") or "").split(",")[0].strip()
        if real:
            return real
    return peer or "unknown"


def enforce_rate_limit(bucket: str, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    recent = [stamp for stamp in _hits.get(bucket, []) if now - stamp < window_seconds]
    if len(recent) >= limit:
        _hits[bucket] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(window_seconds)},
        )
    recent.append(now)
    _hits[bucket] = recent
    if len(_hits) > 20000:
        _hits.clear()


def _is_proxy(address: str) -> bool:
    """Trust X-Real-IP only when the peer is this host or the Docker network."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.is_private or parsed.is_loopback
