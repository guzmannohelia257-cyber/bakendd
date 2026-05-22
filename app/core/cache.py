"""
Cliente Redis opcional.

Si REDIS_URL esta vacio, devuelve None y el codigo llamador debe degradarse
sin romper (no es prerequisito para arrancar la API).

Uso:
    from app.core.cache import get_redis
    r = get_redis()
    if r is not None:
        r.set("k", "v")
"""
from functools import lru_cache
from typing import Optional

from app.core.config import get_settings

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


@lru_cache(maxsize=1)
def get_redis() -> Optional["redis.Redis"]:
    settings = get_settings()
    if not settings.REDIS_URL or redis is None:
        return None
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        return client
    except Exception:
        # No bloqueamos el arranque: si Redis cae la API sigue viva.
        return None
