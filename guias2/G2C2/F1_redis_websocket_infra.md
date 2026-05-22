# F1 — Redis + WebSocket infrastructure

> **Pre-requisito:** Ciclo 1 cerrado. Cliente Redis ya integrado opcionalmente en `app/core/cache.py`.
> **Bloquea:** F2 (broadcast emergencia), F3 (tracking en vivo).
> **Esfuerzo:** 1 día.

## Objetivo
Levantar el canal bidireccional cliente ↔ servidor en tiempo real, escalable a múltiples workers. Sin esta base, las features de tiempo real (broadcast, tracking) no se pueden implementar bien.

Decisiones técnicas:
- **WebSocket nativo de FastAPI** (Starlette) — no necesitamos socket.io.
- **Auth por JWT en query string** (`/ws?token=…`) porque el header `Authorization` no se transmite confiablemente en handshakes WS desde navegador.
- **Redis pub/sub** para que N workers FastAPI/uvicorn compartan eventos — sin esto, dos talleres conectados a distintos workers no ven los mismos eventos.
- **Canales nombrados**: `tenant:{id}`, `incidente:{id}`, `taller:{id}`, `usuario:{id}`. Convención `<recurso>:<id>`.
- **Degradación**: si Redis no está disponible, los WebSockets siguen funcionando dentro de un solo worker (single-instance dev).

---

## Setup de Redis

### Opción A — Docker (recomendada)

Crear `docker-compose.yml` en la raíz del Backend:

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: yary-redis
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

Levantar:
```bash
docker compose up -d redis
docker exec yary-redis redis-cli ping  # debe responder PONG
```

### Opción B — Instalación nativa Windows
- Descargar Memurai (Redis para Windows) o usar WSL2.

### Configurar `.env`
```env
REDIS_URL=redis://localhost:6379/0
```

Verificar que arranca:
```python
# test rapido en consola
.\venv\Scripts\python.exe -c "from app.core.cache import get_redis; r=get_redis(); print('OK:', r.ping() if r else 'redis no disponible')"
```

---

## Arquitectura de archivos

Crear el paquete `app/realtime/`:

```
app/realtime/
├── __init__.py
├── ws_manager.py       # gestion de conexiones in-memory
├── pubsub.py           # wrapper Redis pub/sub multi-worker
├── auth.py             # validacion JWT desde query string
└── endpoints.py        # router WS (/ws)
```

---

## `app/realtime/__init__.py`

```python
from app.realtime.ws_manager import ws_manager
from app.realtime.pubsub import pubsub_broker

__all__ = ["ws_manager", "pubsub_broker"]
```

---

## `app/realtime/ws_manager.py`

```python
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
        # canal -> set de conexiones
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        # conexion -> set de canales (para cleanup rapido)
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
        # Snapshot bajo lock; el send es fuera del lock para no serializar I/O
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
            except Exception as exc:  # conn cerrada, broken pipe, etc.
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

    # Util para tests / debug
    def stats(self) -> dict[str, int]:
        return {c: len(conns) for c, conns in self._channels.items()}


ws_manager = WSManager()
```

---

## `app/realtime/pubsub.py`

```python
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


CHANNEL_PREFIX = "yary:ws:"  # namespace para no colisionar con otros usos de redis


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
                logger.warning("Fallo publish a Redis en %s: %r -> fallback local", channel, exc)

        # Fallback local
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
```

---

## `app/realtime/auth.py`

```python
"""
Auth para WebSocket: extrae JWT del query string `?token=...`
y devuelve identidad + canales a los que el cliente puede suscribirse.
"""
from typing import Optional

from fastapi import WebSocket, status

from app.core.security import verify_token


class WSIdentity:
    def __init__(self, tipo: str, sub_id: int, id_tenant: Optional[int] = None) -> None:
        self.tipo = tipo  # 'usuario' | 'taller' | 'tecnico'
        self.sub_id = sub_id
        self.id_tenant = id_tenant

    @property
    def base_channels(self) -> list[str]:
        """Canales por defecto a los que se suscribe esta identidad."""
        if self.tipo == "taller":
            ch = [f"taller:{self.sub_id}"]
            if self.id_tenant:
                ch.append(f"tenant:{self.id_tenant}")
            return ch
        if self.tipo == "usuario":
            return [f"usuario:{self.sub_id}"]
        if self.tipo == "tecnico":
            ch = [f"usuario:{self.sub_id}"]
            if self.id_tenant:
                ch.append(f"tenant:{self.id_tenant}")
            return ch
        return []


async def authenticate_ws(ws: WebSocket) -> Optional[WSIdentity]:
    """
    Valida el token del query string. Si invalido, cierra el WS con 1008.
    """
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Falta token")
        return None

    payload = verify_token(token)
    if not payload:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token invalido")
        return None

    tipo = payload.get("tipo")
    sub = payload.get("sub")
    tid = payload.get("id_tenant")
    if tipo not in ("usuario", "taller", "tecnico") or sub is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Claims invalidos")
        return None

    try:
        sub_id = int(sub)
        tid_int = int(tid) if tid is not None else None
    except (TypeError, ValueError):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Claims malformados")
        return None

    return WSIdentity(tipo=tipo, sub_id=sub_id, id_tenant=tid_int)
```

---

## `app/realtime/endpoints.py`

```python
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
from app.realtime.pubsub import pubsub_broker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


# Politica de suscripcion: que tipos pueden suscribirse a que prefijos.
# Esto evita que un cliente espie eventos de talleres ajenos.
def _can_subscribe(identity, channel: str) -> bool:
    if identity.tipo == "usuario":
        # cliente solo puede oir su canal de usuario o de incidentes propios
        # (la verificacion de "incidente propio" se delega al servicio que publica)
        return (
            channel == f"usuario:{identity.sub_id}"
            or channel.startswith("incidente:")
        )
    if identity.tipo == "taller":
        return (
            channel == f"taller:{identity.sub_id}"
            or channel == f"tenant:{identity.id_tenant}"
            or channel.startswith("incidente:")  # tras aceptar emergencia
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

    # Suscripcion automatica a los canales base
    await ws_manager.connect(ws, identity.base_channels)
    await ws.send_json({
        "event": "connected",
        "channels": identity.base_channels,
        "identity": {"tipo": identity.tipo, "sub_id": identity.sub_id},
    })

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
                    # No usamos disconnect total: solo sacamos de ese canal
                    async with ws_manager._lock:  # noqa: SLF001
                        ws_manager._channels.get(channel, set()).discard(ws)  # noqa: SLF001
                        ws_manager._reverse.get(ws, set()).discard(channel)  # noqa: SLF001
                    await ws.send_json({"event": "unsubscribed", "channel": channel})

            elif action == "ping":
                await ws.send_json({"event": "pong"})

            else:
                await ws.send_json({"event": "error", "detail": f"accion desconocida: {action}"})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Error en WS: %r", exc)
    finally:
        await ws_manager.disconnect(ws)
```

---

## Cablear en `app/main.py`

Editar `app/main.py` para arrancar/detener el broker y registrar el router WS:

```python
# arriba con los demas imports
from app.realtime import pubsub_broker
from app.realtime.endpoints import router as ws_router

# ...

@app.on_event("startup")
async def _start_realtime() -> None:
    await pubsub_broker.start()


@app.on_event("shutdown")
async def _stop_realtime() -> None:
    await pubsub_broker.stop()


app.include_router(ws_router)
```

> Si tu versión de FastAPI ya recomienda lifespan en vez de `on_event`, refactorizar usando `asynccontextmanager`. El `on_event` sigue funcionando.

---

## Helper para publicar desde endpoints HTTP

Crear `app/services/notify_service.py`:

```python
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
```

> **Importante**: los endpoints HTTP de FastAPI deben ser `async def` para poder llamar a estos helpers con `await`. Si un endpoint actual es síncrono y necesita notificar, usar `from anyio.from_thread import run_sync` o convertir a async.

---

## Frontend (clientes WS)
- **Web Angular**: ver [G2WEB/W4_websocket_client.md](../G2WEB/W4_websocket_client.md)
- **Mobile Flutter**: ver [G2MOBILE/M4_websocket_client.md](../G2MOBILE/M4_websocket_client.md)

---

## Tests `tests/test_ws_infra.py`

```python
"""Tests basicos de la infraestructura WebSocket."""
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token


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
        ws.receive_json()  # connected
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
```

### Test de pub/sub local (sin Redis)

```python
import asyncio
import pytest

from app.realtime.pubsub import pubsub_broker
from app.realtime.ws_manager import ws_manager


@pytest.mark.asyncio
async def test_publish_local_envia_a_ws_manager(monkeypatch):
    """
    Si Redis no esta conectado, publish() debe degradar a ws_manager local.
    """
    pubsub_broker._redis = None  # fuerza local-only

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
```

> Para el segundo test instalar `pytest-asyncio` (ya está) y marcar con `@pytest.mark.asyncio`. En `pytest.ini` agregar `asyncio_mode = auto` o usar marker explícito.

---

## Checklist de cierre F1
- [ ] `docker compose up redis` levanta y `redis-cli ping` responde PONG.
- [ ] `REDIS_URL` configurado en `.env`.
- [ ] `app/realtime/` con los 4 archivos creados.
- [ ] `/ws?token=…` acepta conexiones autenticadas y cierra las inválidas con 1008.
- [ ] Un cliente puede `subscribe` a canales permitidos y le rechaza los prohibidos.
- [ ] `await pubsub_broker.publish("taller:5", {...})` desde un endpoint HTTP llega al WS del taller.
- [ ] Tests `tests/test_ws_infra.py` verdes (≥6 tests).
- [ ] Cliente Angular `RealtimeService` conecta y emite eventos por `events$`.
- [ ] Flutter `RealtimeService` conecta desde emulador (usar `10.0.2.2` en Android emu).

## Notas / troubleshooting
- **"WebSocketDisconnect en TestClient"**: el TestClient sincrónico cierra el WS al salir del `with`. Usar `pytest.raises` solo si esperas error de conexión.
- **CORS para WS**: el middleware CORS de Starlette no aplica a WS handshakes. La autenticación por token en query string ya nos protege.
- **Token expira mientras WS está conectado**: el cliente debe reconectar con token fresco al detectar `1008`. El servidor no rechaza tokens en flight (solo en handshake).
- **Multi-worker con uvicorn**: `uvicorn app.main:app --workers 4` — cada worker tiene su `ws_manager` local; Redis sincroniza eventos. Sin Redis, eventos publicados en worker A no llegan a clientes conectados a worker B.
- **Heartbeat**: si tu proxy/firewall corta conexiones idle, agregar ping del lado servidor cada 30s (asyncio task por conexión).
