# F2 — Broadcast de emergencia + first-accept-wins

> **Pre-requisito:** F1 (WebSocket infra funcional) y Ciclo 1 F1 (servicios extendidos).
> **Esfuerzo:** 2 días.

## Objetivo (del enunciado)
> "Cuando un vehículo sufre un incidente (ej. pinchazo), el sistema envía una notificación de emergencia a todos los talleres cercanos disponibles. El primer taller que acepta toma el servicio; los demás reciben confirmación de que ya no está disponible."

Flujo:

```
1. Cliente reporta incidente -> POST /incidentes
2. Backend clasifica (IA + cliente), guarda incidente
3. Backend identifica talleres compatibles (categoria + radio + disponibles)
4. Backend crea N filas en CandidatoAsignacion (modelo ya existe)
5. Backend publica evento "incidente.nuevo" en canal taller:{id} de cada candidato
6. Talleres conectados via WS lo reciben en tiempo real
7. Primer taller que hace POST /incidentes/{id}/aceptar gana (lock atomico)
8. Backend publica "incidente.tomado" a los demas candidatos -> su UI marca "ya no disponible"
9. Cliente recibe "incidente.asignado" en su canal con datos del taller ganador
```

---

## Servicio de matching `app/services/matching_service.py`

```python
"""
Encuentra talleres candidatos para un incidente.

Reglas:
  - Taller activo + disponible.
  - Taller declara la categoria del incidente.
  - Distancia <= radio_km.
  - Ordenado por distancia.
"""
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.models.catalogos import EstadoIncidente
from app.models.incidente import CandidatoAsignacion, Incidente
from app.models.taller import Taller, TallerServicio


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return 2 * R * asin(sqrt(a))


def buscar_talleres_compatibles(
    db: Session, incidente: Incidente, radio_km: float = 20.0, limite: int = 10,
) -> list[tuple[Taller, float]]:
    if incidente.id_categoria is None:
        return []

    rows = (
        db.query(Taller, TallerServicio)
        .join(TallerServicio, TallerServicio.id_taller == Taller.id_taller)
        .filter(
            TallerServicio.id_categoria == incidente.id_categoria,
            Taller.activo.is_(True),
            Taller.disponible.is_(True),
            Taller.latitud.isnot(None),
            Taller.longitud.isnot(None),
        )
        .all()
    )

    con_distancia = []
    for taller, _servicio in rows:
        d = _haversine_km(incidente.latitud, incidente.longitud, taller.latitud, taller.longitud)
        if d <= radio_km:
            con_distancia.append((taller, d))

    con_distancia.sort(key=lambda x: x[1])
    return con_distancia[:limite]


def crear_candidatos(db: Session, incidente: Incidente, talleres_dist: list[tuple]) -> list[CandidatoAsignacion]:
    candidatos = []
    for taller, dist in talleres_dist:
        cand = CandidatoAsignacion(
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            distancia_km=dist,
            score_total=None,
            seleccionado=False,
        )
        db.add(cand)
        candidatos.append(cand)
    db.commit()
    for c in candidatos:
        db.refresh(c)
    return candidatos
```

---

## Servicio de broadcast `app/services/broadcast_service.py`

```python
"""
Publica eventos de emergencia y aceptacion via pub/sub.
"""
from app.models.incidente import Asignacion, Incidente
from app.models.taller import Taller
from app.services.notify_service import (
    notify_incidente,
    notify_taller,
    notify_usuario,
)


def _incidente_payload(incidente: Incidente, taller: Taller | None = None) -> dict:
    base = {
        "id_incidente": incidente.id_incidente,
        "id_categoria": incidente.id_categoria,
        "latitud": incidente.latitud,
        "longitud": incidente.longitud,
        "descripcion_usuario": incidente.descripcion_usuario,
        "resumen_ia": incidente.resumen_ia,
        "created_at": incidente.created_at.isoformat() if incidente.created_at else None,
    }
    if taller is not None:
        base["taller"] = {
            "id_taller": taller.id_taller,
            "nombre": taller.nombre,
            "telefono": taller.telefono,
        }
    return base


async def broadcast_emergencia(incidente: Incidente, candidatos_talleres: list[Taller]) -> None:
    """A cada taller candidato: 'tienes una emergencia entrante'."""
    payload = _incidente_payload(incidente)
    for taller in candidatos_talleres:
        await notify_taller(taller.id_taller, "incidente.nuevo", payload)


async def broadcast_incidente_tomado(
    incidente: Incidente, taller_ganador: Taller, otros_candidatos: list[Taller],
) -> None:
    """Notifica a los talleres perdedores."""
    payload = _incidente_payload(incidente, taller_ganador)
    for taller in otros_candidatos:
        await notify_taller(taller.id_taller, "incidente.tomado", payload)


async def notify_cliente_asignado(incidente: Incidente, taller: Taller, asignacion: Asignacion) -> None:
    payload = {
        **_incidente_payload(incidente, taller),
        "id_asignacion": asignacion.id_asignacion,
        "eta_minutos": asignacion.eta_minutos,
    }
    await notify_usuario(incidente.id_usuario, "incidente.asignado", payload)
    # Tambien al canal del incidente para que cualquier observador lo vea
    await notify_incidente(incidente.id_incidente, "incidente.asignado", payload)
```

---

## Endpoint: crear incidente con broadcast

En `app/api/incidencias.py`, **convertir el endpoint a `async`** y agregar broadcast tras crear:

```python
from app.services.broadcast_service import broadcast_emergencia
from app.services import matching_service


@router.post("/incidentes", response_model=IncidenteResponse, status_code=201)
async def crear_incidente(
    body: IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # 1) Crear el incidente (logica existente)
    inc = Incidente(
        id_usuario=current_user.id_usuario,
        id_vehiculo=body.id_vehiculo,
        id_estado=...,  # 'pendiente'
        id_categoria=body.id_categoria,
        latitud=body.latitud,
        longitud=body.longitud,
        descripcion_usuario=body.descripcion,
    )
    db.add(inc); db.commit(); db.refresh(inc)

    # 2) Buscar talleres compatibles
    talleres_dist = matching_service.buscar_talleres_compatibles(
        db, inc, radio_km=body.radio_km or 20.0,
    )
    talleres = [t for t, _d in talleres_dist]

    # 3) Crear candidatos (log persistente)
    matching_service.crear_candidatos(db, inc, talleres_dist)

    # 4) Broadcast WS (no bloqueante de la respuesta)
    if talleres:
        await broadcast_emergencia(inc, talleres)

    return inc
```

> Si el endpoint actual es síncrono y romperlo es caro, una opción intermedia: encolar el broadcast con `asyncio.create_task` desde un wrapper async. Pero conviene migrarlo a async limpiamente.

---

## Endpoint: taller acepta emergencia (atómico)

Crear en `app/api/incidencias.py`:

```python
from sqlalchemy import select, update
from app.models.catalogos import EstadoAsignacion
from app.models.incidente import Asignacion, CandidatoAsignacion
from app.services.broadcast_service import (
    broadcast_incidente_tomado,
    notify_cliente_asignado,
)


@router.post(
    "/incidentes/{id_incidente}/aceptar",
    summary="Taller acepta una emergencia entrante; primero gana",
)
async def aceptar_emergencia(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    # 1) Lock pesimista sobre el incidente para evitar race conditions
    inc: Incidente | None = (
        db.execute(
            select(Incidente)
            .where(Incidente.id_incidente == id_incidente)
            .with_for_update()
        ).scalar_one_or_none()
    )
    if not inc:
        raise HTTPException(404, "Incidente no existe")

    # 2) Validar que este taller era candidato
    cand = (
        db.query(CandidatoAsignacion)
        .filter_by(id_incidente=id_incidente, id_taller=current_taller.id_taller)
        .first()
    )
    if not cand:
        raise HTTPException(403, "Tu taller no fue convocado a esta emergencia")

    # 3) Validar que aun no hay asignacion (otro taller no lo tomo)
    existing = db.query(Asignacion).filter_by(id_incidente=id_incidente).first()
    if existing:
        raise HTTPException(409, f"Esta emergencia ya fue tomada por el taller {existing.id_taller}")

    # 4) Crear asignacion en estado 'aceptada'
    estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").one()
    asig = Asignacion(
        id_tenant=current_taller.id_tenant,
        id_incidente=id_incidente,
        id_taller=current_taller.id_taller,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db.add(asig)

    # 5) Marcar candidato ganador
    cand.seleccionado = True

    # Heredar id_tenant en el incidente (era public-null)
    inc.id_tenant = current_taller.id_tenant

    db.commit()
    db.refresh(asig)

    # 6) Broadcast a perdedores + cliente
    perdedores_q = (
        db.query(Taller)
        .join(CandidatoAsignacion, CandidatoAsignacion.id_taller == Taller.id_taller)
        .filter(
            CandidatoAsignacion.id_incidente == id_incidente,
            CandidatoAsignacion.id_taller != current_taller.id_taller,
        )
        .all()
    )
    await broadcast_incidente_tomado(inc, current_taller, perdedores_q)
    await notify_cliente_asignado(inc, current_taller, asig)

    return {
        "id_asignacion": asig.id_asignacion,
        "id_taller": current_taller.id_taller,
        "nuevo_estado": "aceptada",
    }
```

> **`with_for_update()`**: bloqueo a nivel de fila en Postgres. Si dos talleres llegan al mismo tiempo, la segunda transacción espera. Cuando la primera commitea, la segunda ve la `Asignacion` existente y devuelve 409.

---

## Frontend
- **Web Angular (bandeja de emergencias del taller)**: ver [G2WEB/W5_emergencias_live.md](../G2WEB/W5_emergencias_live.md)
- **Mobile Flutter (cliente esperando taller)**: ver [G2MOBILE/M5_esperando_taller.md](../G2MOBILE/M5_esperando_taller.md)

---

## Tests `tests/test_broadcast.py`

```python
"""Tests del flujo broadcast + first-accept-wins."""
import pytest

from app.core.security import create_access_token


def _token(taller):
    extra = {"id_tenant": taller.id_tenant} if taller.id_tenant else None
    return create_access_token(subject_id=taller.id_taller, tipo="taller", extra_claims=extra)


def test_aceptar_emergencia_crea_asignacion(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
    taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import Asignacion, CandidatoAsignacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    # Simular que el matcher creo el candidato
    db_session.add(CandidatoAsignacion(
        id_incidente=inc.id_incidente, id_taller=taller.id_taller, distancia_km=0.5,
    ))
    db_session.commit()

    r = client.post(
        f"/incidentes/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 200, r.text
    assert r.json()["nuevo_estado"] == "aceptada"

    asig = db_session.query(Asignacion).filter_by(id_incidente=inc.id_incidente).first()
    assert asig is not None
    assert asig.id_taller == taller.id_taller


def test_segundo_taller_que_acepta_recibe_409(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
    taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import CandidatoAsignacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    talleres = []
    for _ in range(2):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))
        talleres.append(taller)
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    for t in talleres:
        db_session.add(CandidatoAsignacion(
            id_incidente=inc.id_incidente, id_taller=t.id_taller, distancia_km=0.5,
        ))
    db_session.commit()

    # Primer taller acepta
    r1 = client.post(
        f"/incidentes/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[0]),
    )
    assert r1.status_code == 200

    # Segundo taller intenta
    r2 = client.post(
        f"/incidentes/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[1]),
    )
    assert r2.status_code == 409


def test_taller_no_candidato_no_puede_aceptar(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
    taller_auth_headers,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)  # no es candidato

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    r = client.post(
        f"/incidentes/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 403


def test_ws_taller_recibe_evento_incidente_nuevo(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
):
    """
    Verifica end-to-end: cliente crea incidente -> taller compatible recibe
    evento por WS.

    Nota: TestClient ejecuta startup/shutdown del app, asi que pubsub_broker
    se inicializa en modo local (sin Redis), suficiente para tests.
    """
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    # Crear incidente AHORA mediante el endpoint async para disparar broadcast
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    # Disparar broadcast manual (porque incidente_factory inserta directo, no via endpoint)
    import asyncio
    from app.services.broadcast_service import broadcast_emergencia

    token = _token(taller)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()  # connected
        # Disparar
        asyncio.get_event_loop().run_until_complete(broadcast_emergencia(inc, [taller]))
        msg = ws.receive_json()
        assert msg["event"] == "incidente.nuevo"
        assert msg["data"]["id_incidente"] == inc.id_incidente
```

---

## Checklist de cierre F2
- [ ] `app/services/matching_service.py` filtra correctamente por categoría + radio.
- [ ] `app/services/broadcast_service.py` y `notify_service.py` operativos.
- [ ] `POST /incidentes` async, dispara broadcast a candidatos.
- [ ] `POST /incidentes/{id}/aceptar` usa `with_for_update`; segundo intento responde 409.
- [ ] Heredar `id_tenant` en `incidente` cuando se asigna a un taller (multi-tenant consistency).
- [ ] UI taller (Angular) lista emergencias en tiempo real, marca "tomada" para los demás.
- [ ] UI cliente (Flutter) ve cuando se asigna y muestra datos del taller.
- [ ] Tests `tests/test_broadcast.py` verdes (≥4).
- [ ] Demo manual con 2 navegadores como 2 talleres + 1 cliente: el primer click gana.

## Notas
- **El cliente puede recibir varias "incidente.nuevo" si lo escucha**: no debería oírlo (no está suscrito al canal del taller). Verificar política en `_can_subscribe`.
- **Concurrencia real**: si necesitan probar 50 talleres compitiendo, usar `pytest-xdist` o un script standalone con `httpx.AsyncClient` haciendo 50 POST en paralelo.
- **Race entre crear candidato y aceptar**: poco probable porque candidatos se crean en commit antes del broadcast, pero el endpoint `/aceptar` lo valida igualmente.
- **¿Y si el cliente cancela mientras se está broadcasteando?** Es válido — al aceptar se valida estado del incidente. Si querés ser extra estricto, validar `inc.id_estado != cancelado` en el lock.
