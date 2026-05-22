"""
Manager in-memory de conexiones WebSocket activas por canal.

Cada worker tiene SU PROPIO manager (la memoria no se comparte entre procesos).
Para que dos workers se enteren de eventos de cada uno, ver pubsub.py
(Redis pub/sub).

Convencion de canales:
  - tenant:{id}      - eventos globales del tenant (broadcast a todos sus talleres y miembros)
  - incidente:{id}   - actualizaciones de un incidente especifico (cliente lo ve)
  - taller:{id}      - notificaciones a un taller (emergencias entrantes, cotizaciones)
  - usuario:{id}     - canal privado de un usuario (cliente o tecnico)
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._reverse: dict[WebSocket, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, channels: list[str]) -> None:
        """Asume que ws.accept() ya se llamo."""
        async with self._lock:
            for c in channels:
                self._channels[c].add(ws)
                self._reverse[ws].add(c)
        logger.info("WS connected to channels %s", channels)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            for c in list(self._reverse.get(ws, ())):
                self._channels[c].discard(ws)
                if not self._channels[c]:
                    self._channels.pop(c, None)
            self._reverse.pop(ws, None)

    async def send_to_channel(self, channel: str, payload: dict[str, Any]) -> int:
        """
        Envia payload a TODAS las conexiones de un canal en este worker.
        Devuelve el numero de conexiones a las que se envio.
        """
        async with self._lock:
            conns = list(self._channels.get(channel, ()))
        if not conns:
            return 0

        dead: list[WebSocket] = []
        sent = 0
        for ws in conns:
            try:
                await ws.send_json(payload)
                sent += 1
            except Exception as exc:
                logger.warning("WS send fallo en canal %s: %r", channel, exc)
                dead.append(ws)

        for d in dead:
            await self.disconnect(d)
        return sent

    async def send_to_channels(self, channels: list[str], payload: dict[str, Any]) -> int:
        total = 0
        for c in channels:
            total += await self.send_to_channel(c, payload)
        return total

    def stats(self) -> dict[str, int]:
        return {c: len(conns) for c, conns in self._channels.items()}


ws_manager = WSManager()
