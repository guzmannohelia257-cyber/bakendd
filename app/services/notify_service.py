"""
Helpers para emitir eventos en tiempo real desde endpoints HTTP.
"""
from typing import Any

from app.realtime.pubsub import pubsub_broker


async def notify_tenant(id_tenant: int, event: str, data: dict[str, Any]) -> None:
    await pubsub_broker.publish(f"tenant:{id_tenant}", {"event": event, "data": data})


async def notify_taller(id_taller: int, event: str, data: dict[str, Any]) -> None:
    await pubsub_broker.publish(f"taller:{id_taller}", {"event": event, "data": data})


async def notify_incidente(id_incidente: int, event: str, data: dict[str, Any]) -> None:
    await pubsub_broker.publish(f"incidente:{id_incidente}", {"event": event, "data": data})


async def notify_usuario(id_usuario: int, event: str, data: dict[str, Any]) -> None:
    await pubsub_broker.publish(f"usuario:{id_usuario}", {"event": event, "data": data})
