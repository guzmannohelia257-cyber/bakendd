"""
Endpoint WebSocket principal: /ws

Protocolo de cliente:
  cliente conecta -> ws://host/ws?token=JWT
  server suscribe automaticamente a `base_channels` segun identidad
  cliente puede enviar:
    {"action": "subscribe", "channel": "incidente:42"}
    {"action": "unsubscribe", "channel": "incidente:42"}
    {"action": "ping"}
  server envia eventos arbitrarios:
    {"event": "incidente.nuevo", "data": {...}, "channel": "taller:5"}
"""
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.auth import authenticate_ws
from app.realtime.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


def _can_subscribe(identity, channel: str) -> bool:
    if identity.tipo == "usuario":
        return channel == f"usuario:{identity.sub_id}" or channel.startswith("incidente:")
    if identity.tipo == "taller":
        return (
            channel == f"taller:{identity.sub_id}"
            or channel == f"tenant:{identity.id_tenant}"
            or channel.startswith("incidente:")
        )
    if identity.tipo == "tecnico":
        return (
            channel == f"usuario:{identity.sub_id}"
            or channel == f"tenant:{identity.id_tenant}"
            or channel.startswith("incidente:")
        )
    return False


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    identity = await authenticate_ws(ws)
    if not identity:
        return

    await ws_manager.connect(ws, identity.base_channels)
    await ws.send_json(
        {
            "event": "connected",
            "channels": identity.base_channels,
            "identity": {"tipo": identity.tipo, "sub_id": identity.sub_id},
        }
    )

    try:
        while True:
            msg: dict[str, Any] = await ws.receive_json()
            action = msg.get("action")

            if action == "subscribe":
                channel = msg.get("channel")
                if not channel or not _can_subscribe(identity, channel):
                    await ws.send_json({"event": "error", "detail": "subscribe rechazado"})
                    continue
                await ws_manager.connect(ws, [channel])
                await ws.send_json({"event": "subscribed", "channel": channel})

            elif action == "unsubscribe":
                channel = msg.get("channel")
                if channel:
                    async with ws_manager._lock:  # noqa: SLF001
                        ws_manager._channels.get(channel, set()).discard(ws)  # noqa: SLF001
                        ws_manager._reverse.get(ws, set()).discard(channel)  # noqa: SLF001
                    await ws.send_json({"event": "unsubscribed", "channel": channel})

            elif action == "ping":
                await ws.send_json({"event": "pong"})

            else:
                await ws.send_json(
                    {"event": "error", "detail": f"accion desconocida: {action}"}
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Error en WS: %r", exc)
    finally:
        await ws_manager.disconnect(ws)
