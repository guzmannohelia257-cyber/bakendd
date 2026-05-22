"""Tests basicos de la infraestructura WebSocket."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.realtime.pubsub import pubsub_broker
from app.realtime.ws_manager import ws_manager


def _token_taller(taller) -> str:
    extra = {"id_tenant": taller.id_tenant} if taller.id_tenant else None
    return create_access_token(subject_id=taller.id_taller, tipo="taller", extra_claims=extra)


def test_ws_rechaza_sin_token(client: TestClient):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()


def test_ws_rechaza_token_invalido(client: TestClient):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=basura") as ws:
            ws.receive_json()


def test_ws_taller_conecta_y_recibe_evento_connected(client, tenant_factory, taller_factory):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    token = _token_taller(taller)

    with client.websocket_connect(f"/ws?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "connected"
        assert f"taller:{taller.id_taller}" in msg["channels"]
        assert f"tenant:{tenant.id_tenant}" in msg["channels"]


def test_ws_subscribe_a_incidente(client, tenant_factory, taller_factory):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    token = _token_taller(taller)

    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"action": "subscribe", "channel": "incidente:123"})
        ack = ws.receive_json()
        assert ack["event"] == "subscribed"
        assert ack["channel"] == "incidente:123"


def test_ws_ping_pong(client, tenant_factory, taller_factory):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    token = _token_taller(taller)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"action": "ping"})
        assert ws.receive_json() == {"event": "pong"}


def test_ws_rechaza_subscribe_a_canal_no_autorizado(client, cliente_factory, cliente_auth_headers):
    """Un cliente NO debe poder suscribirse al canal de un taller."""
    cliente = cliente_factory()
    headers = cliente_auth_headers(cliente)
    token = headers["Authorization"].split(" ")[1]

    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"action": "subscribe", "channel": "taller:99"})
        resp = ws.receive_json()
        assert resp["event"] == "error"


@pytest.mark.asyncio
async def test_publish_local_envia_a_ws_manager():
    """
    Si Redis no esta conectado, publish() debe degradar a ws_manager local.
    """
    pubsub_broker._redis = None

    recibidos = []

    class FakeWS:
        async def send_json(self, payload):
            recibidos.append(payload)

    fake = FakeWS()
    await ws_manager.connect(fake, ["test-channel"])  # type: ignore[arg-type]
    await pubsub_broker.publish("test-channel", {"event": "hola"})

    await asyncio.sleep(0.05)
    assert {"event": "hola"} in recibidos
    await ws_manager.disconnect(fake)  # type: ignore[arg-type]
