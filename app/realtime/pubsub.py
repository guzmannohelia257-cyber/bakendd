"""
Wrapper Redis pub/sub para coordinar eventos entre workers.

Flujo:
  1. Un endpoint HTTP/WS publica un evento -> broker.publish(canal, payload)
     - Esto hace SET en Redis. Todos los workers suscritos al canal lo reciben.
  2. Cada worker corre _listen() en background. Cuando recibe un mensaje,
     lo reenvia a sus conexiones WS locales (ws_manager.send_to_channel).

Si REDIS_URL esta vacio o Redis no responde, el broker entra en modo
"local-only": publish() solo envia a ws_manager local sin pasar por Redis.
Funciona en dev/single-worker pero NO escala.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.config import get_settings
from app.realtime.ws_manager import ws_manager

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore


CHANNEL_PREFIX = "yary:ws:"


class PubSubBroker:
    def __init__(self) -> None:
        self._redis: "aioredis.Redis | None" = None
        self._pubsub: Any = None
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        settings = get_settings()
        if not settings.REDIS_URL or aioredis is None:
            logger.warning("REDIS_URL vacio o redis no instalado -> modo local-only")
            return
        try:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await self._redis.ping()
        except Exception as exc:
            logger.warning("No se pudo conectar a Redis (%r) -> local-only", exc)
            self._redis = None
            return

        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
        self._running = True
        self._task = asyncio.create_task(self._listen(), name="ws-pubsub-listener")
        logger.info("PubSub broker conectado a Redis")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        """
        Publica un evento al canal logico. Si Redis esta disponible, lo envia via
        pub/sub (todos los workers lo reciben). Si no, lo manda solo localmente.
        """
        if self._redis is not None:
            try:
                await self._redis.publish(f"{CHANNEL_PREFIX}{channel}", json.dumps(payload))
                return
            except Exception as exc:
                logger.warning(
                    "Fallo publish a Redis en %s: %r -> fallback local", channel, exc
                )

        await ws_manager.send_to_channel(channel, payload)

    async def _listen(self) -> None:
        assert self._pubsub
        async for message in self._pubsub.listen():
            if not self._running:
                break
            if message["type"] not in ("pmessage", "message"):
                continue
            try:
                full_channel = message["channel"]
                if isinstance(full_channel, bytes):
                    full_channel = full_channel.decode()
                logical_channel = full_channel.removeprefix(CHANNEL_PREFIX)
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                payload = json.loads(data)
                await ws_manager.send_to_channel(logical_channel, payload)
            except Exception as exc:
                logger.exception("Error procesando pubsub message: %r", exc)


pubsub_broker = PubSubBroker()
