# F3 — Tracking GPS en vivo + ETA

> **Pre-requisito:** F1 (WebSocket).
> **Esfuerzo:** 2 días.

## Objetivo (del enunciado)
> "Tracking en vivo del vehículo del taller que va en camino: posición actual, ETA, alertas de tráfico, visualización en mapa."

Flujo:

```
1. Tecnico acepta asignacion -> POST /asignaciones/{id}/iniciar-viaje
2. App Flutter del tecnico envia su lat/lng cada 10-15s
   -> POST /tecnicos/me/ubicacion
3. Backend persiste la ubicacion + publica via WS al canal incidente:{id}
4. App Flutter del cliente recibe y mueve el marker en mapa
5. ETA se calcula:
   - opcion A: tiempo restante = distancia/velocidad_promedio (rapido, suficiente para demo)
   - opcion B: OSRM publico (https://router.project-osrm.org) - mejor precision
6. Cuando tecnico entra en radio de 100m del incidente -> auto cambia estado a 'llegado'
```

---

## Migración `0007_ubicacion_tecnico`

```bash
.\venv\Scripts\alembic.exe revision -m "0007_ubicacion_tecnico"
```

Contenido:

```python
"""0007_ubicacion_tecnico

Tabla historica de posiciones del tecnico para reconstruir tracking pasado.
Se inserta en cada beat. Sin RLS aqui porque el filtro tenant ya aplica via
id_tenant de columna heredada.

Tambien anade lat/lng/timestamp redundantes en usuario_taller para queries
rapidas de "ultima posicion conocida".
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "REEMPLAZAR_POR_HASH"
down_revision: Union[str, None] = "REVISION_DE_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ubicacion_tecnico",
        sa.Column("id_ubicacion", sa.BigInteger(), primary_key=True),
        sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=False, index=True),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False, index=True),
        sa.Column("id_asignacion", sa.Integer(), sa.ForeignKey("asignacion.id_asignacion"), nullable=True, index=True),
        sa.Column("latitud", sa.Float(), nullable=False),
        sa.Column("longitud", sa.Float(), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("velocidad_kmh", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ubicacion_tecnico_asig_time", "ubicacion_tecnico", ["id_asignacion", "created_at"])
    # ultima posicion conocida ya esta en usuario_taller.lat/lng (sobreescribir al insertar)


def downgrade() -> None:
    op.drop_index("ix_ubicacion_tecnico_asig_time", table_name="ubicacion_tecnico")
    op.drop_table("ubicacion_tecnico")
```

---

## Modelo `app/models/ubicacion.py`

```python
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.sql import func

from app.db.session import Base


class UbicacionTecnico(Base):
    __tablename__ = "ubicacion_tecnico"

    id_ubicacion = Column(BigInteger, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    id_asignacion = Column(Integer, ForeignKey("asignacion.id_asignacion"), nullable=True, index=True)

    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    velocidad_kmh = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

Registrar en `app/models/__init__.py`.

---

## Schemas `app/schemas/tracking_schema.py`

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UbicacionPing(BaseModel):
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = Field(None, ge=0, le=1000)
    velocidad_kmh: Optional[float] = Field(None, ge=0, le=300)
    id_asignacion: Optional[int] = Field(None, description="Si va asociado a una asignacion activa")


class EtaResponse(BaseModel):
    distancia_km: float
    eta_segundos: int
    eta_minutos: int


class UbicacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latitud: float
    longitud: float
    created_at: datetime
    velocidad_kmh: Optional[float] = None
```

---

## Servicio `app/services/tracking_service.py`

```python
"""
Servicio de tracking + ETA.

ETA usa OSRM publico por defecto (sin API key). Si OSRM_URL en .env apunta a
otra instancia se usa esa. Si todo falla, fallback a calculo simple por
distancia / velocidad_promedio (40 km/h en ciudad).
"""
from __future__ import annotations

import logging
import os
from math import asin, cos, radians, sin, sqrt

import httpx

logger = logging.getLogger(__name__)

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
VELOCIDAD_DEFAULT_KMH = 40.0
GEOFENCE_RADIO_M = 100.0


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return 2 * R * asin(sqrt(a))


async def calcular_eta(
    lat_origen: float, lng_origen: float,
    lat_destino: float, lng_destino: float,
) -> tuple[float, int]:
    """
    Devuelve (distancia_km, eta_segundos).
    """
    # Distancia de respaldo
    d_km = haversine_km(lat_origen, lng_origen, lat_destino, lng_destino)
    fallback_eta = int((d_km / VELOCIDAD_DEFAULT_KMH) * 3600)

    # OSRM: /route/v1/driving/lon1,lat1;lon2,lat2?overview=false
    url = f"{OSRM_URL}/route/v1/driving/{lng_origen},{lat_origen};{lng_destino},{lat_destino}?overview=false"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                return route["distance"] / 1000.0, int(route["duration"])
    except Exception as exc:
        logger.warning("OSRM fallo (%r). Usando fallback haversine.", exc)

    return d_km, fallback_eta


def llego_geofence(
    lat_tecnico: float, lng_tecnico: float, lat_inc: float, lng_inc: float,
) -> bool:
    d_km = haversine_km(lat_tecnico, lng_tecnico, lat_inc, lng_inc)
    return d_km * 1000 <= GEOFENCE_RADIO_M
```

---

## Endpoint: técnico envía ubicación

En `app/api/tecnicos.py` (agregar):

```python
from app.models.incidente import Asignacion, HistorialEstadoAsignacion, Incidente
from app.models.catalogos import EstadoAsignacion
from app.models.ubicacion import UbicacionTecnico
from app.models.usuario_taller import UsuarioTaller
from app.schemas.tracking_schema import UbicacionPing, EtaResponse, UbicacionResponse
from app.services import tracking_service
from app.services.notify_service import notify_incidente


@router.post(
    "/me/ubicacion",
    summary="Tecnico envia su ubicacion actual (cada 10-15s mientras va en viaje)",
)
async def reportar_ubicacion(
    body: UbicacionPing,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(403, "Solo tecnicos pueden reportar ubicacion")

    # Vinculo a un taller (el primero activo)
    vinculo = (
        db.query(UsuarioTaller)
        .filter(
            UsuarioTaller.id_usuario == current_user.id_usuario,
            UsuarioTaller.activo.is_(True),
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(400, "Tecnico sin taller asociado")

    # Actualizar "ultima posicion conocida" en usuario_taller
    vinculo.latitud = body.latitud
    vinculo.longitud = body.longitud

    # Insertar punto historico (solo si hay asignacion activa, para no inflar BD)
    asig: Asignacion | None = None
    if body.id_asignacion:
        asig = db.query(Asignacion).get(body.id_asignacion)
        if not asig or asig.id_taller != vinculo.id_taller:
            raise HTTPException(403, "Esa asignacion no es de tu taller")

        db.add(UbicacionTecnico(
            id_tenant=vinculo.taller.id_tenant,
            id_usuario=current_user.id_usuario,
            id_asignacion=asig.id_asignacion,
            latitud=body.latitud,
            longitud=body.longitud,
            accuracy_m=body.accuracy_m,
            velocidad_kmh=body.velocidad_kmh,
        ))

    db.commit()

    # Broadcast posicion al canal del incidente
    eta_resp = None
    llegado_auto = False
    if asig:
        incidente = db.query(Incidente).get(asig.id_incidente)

        dist_km, eta_seg = await tracking_service.calcular_eta(
            body.latitud, body.longitud, incidente.latitud, incidente.longitud,
        )
        eta_resp = {
            "distancia_km": round(dist_km, 2),
            "eta_segundos": eta_seg,
            "eta_minutos": round(eta_seg / 60),
        }

        await notify_incidente(asig.id_incidente, "tecnico.posicion", {
            "id_asignacion": asig.id_asignacion,
            "latitud": body.latitud,
            "longitud": body.longitud,
            "eta": eta_resp,
        })

        # Geofencing: si llego, cambiar estado
        if tracking_service.llego_geofence(
            body.latitud, body.longitud, incidente.latitud, incidente.longitud
        ) and asig.estado.nombre in ("aceptada", "en_camino"):
            estado_llegado = db.query(EstadoAsignacion).filter_by(nombre="llegado").first()
            if estado_llegado:
                db.add(HistorialEstadoAsignacion(
                    id_asignacion=asig.id_asignacion,
                    id_estado_anterior=asig.id_estado_asignacion,
                    id_estado_nuevo=estado_llegado.id_estado_asignacion,
                    observacion="Auto: geofencing (radio 100m)",
                ))
                asig.id_estado_asignacion = estado_llegado.id_estado_asignacion
                db.commit()
                llegado_auto = True
                await notify_incidente(asig.id_incidente, "asignacion.llegado", {
                    "id_asignacion": asig.id_asignacion,
                })

    return {"ok": True, "eta": eta_resp, "llegado_auto": llegado_auto}
```

---

## Endpoint: cliente consulta ETA actual

```python
@router.get(
    "/asignaciones/{id_asignacion}/eta",
    response_model=EtaResponse,
    summary="ETA actual del tecnico hacia el incidente",
)
async def obtener_eta(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.core.tenant_context import current_tenant
    tok = current_tenant.set(0)  # cliente publico
    try:
        asig = db.query(Asignacion).get(id_asignacion)
    finally:
        current_tenant.reset(tok)
    if not asig:
        raise HTTPException(404, "Asignacion no existe")
    incidente = asig.incidente
    if incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(403, "No es tu asignacion")

    ultimo = (
        db.query(UbicacionTecnico)
        .filter(UbicacionTecnico.id_asignacion == id_asignacion)
        .order_by(UbicacionTecnico.created_at.desc())
        .first()
    )
    if not ultimo:
        raise HTTPException(404, "Aun no hay ubicacion registrada")

    dist_km, eta_seg = await tracking_service.calcular_eta(
        ultimo.latitud, ultimo.longitud, incidente.latitud, incidente.longitud,
    )
    return EtaResponse(
        distancia_km=round(dist_km, 2),
        eta_segundos=eta_seg,
        eta_minutos=round(eta_seg / 60),
    )
```

---

## Frontend
- **Mobile Flutter (cliente ve mapa)**: ver [G2MOBILE/M6_tracking_mapa.md](../G2MOBILE/M6_tracking_mapa.md)
- **Mobile Flutter (técnico envía GPS)**: ver [G2MOBILE/M7_location_sender.md](../G2MOBILE/M7_location_sender.md)

> El cliente final ve el mapa en la app móvil. El panel web del taller puede usar el mismo endpoint si se necesita visualización web del técnico (no implementado en C2).

---

## Tests `tests/test_tracking.py`

```python
"""Tests de tracking + ETA."""
import pytest


def _vincular_tecnico_a_taller(db_session, cliente_factory, taller, hash_password_fn):
    """Crea usuario rol=3 vinculado al taller."""
    from app.models.usuario import Usuario
    from app.models.usuario_taller import UsuarioTaller

    import uuid
    u = Usuario(
        id_rol=3,
        nombre="Tecnico Test",
        email=f"tec-{uuid.uuid4().hex[:6]}@test.example.com",
        password_hash=hash_password_fn("tec12345"),
    )
    db_session.add(u); db_session.commit(); db_session.refresh(u)

    vin = UsuarioTaller(id_usuario=u.id_usuario, id_taller=taller.id_taller, activo=True)
    db_session.add(vin); db_session.commit()
    return u


def test_reportar_ubicacion_sin_asignacion_solo_actualiza_vinculo(
    client, db_session, tenant_factory, taller_factory,
):
    from app.core.security import hash_password, create_access_token
    from app.models.usuario_taller import UsuarioTaller

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _vincular_tecnico_a_taller(db_session, None, taller, hash_password)

    token = create_access_token(subject_id=tecnico.id_usuario, tipo="usuario")
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={"latitud": -16.5, "longitud": -68.15},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    vin = db_session.query(UsuarioTaller).filter_by(id_usuario=tecnico.id_usuario).first()
    assert vin.latitud == -16.5
    assert vin.longitud == -68.15


def test_reportar_ubicacion_con_asignacion_inserta_historico_y_calcula_eta(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
):
    from app.core.security import hash_password, create_access_token
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion
    from app.models.ubicacion import UbicacionTecnico

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _vincular_tecnico_a_taller(db_session, None, taller, hash_password)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, lat=-16.500, lng=-68.150)

    estado_aceptada = db_session.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc.id_incidente,
        id_taller=taller.id_taller,
        id_usuario=tecnico.id_usuario,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db_session.add(asig); db_session.commit(); db_session.refresh(asig)

    token = create_access_token(subject_id=tecnico.id_usuario, tipo="usuario")
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.510, "longitud": -68.160,
            "id_asignacion": asig.id_asignacion,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["eta"]["distancia_km"] > 0

    hist = db_session.query(UbicacionTecnico).filter_by(id_asignacion=asig.id_asignacion).all()
    assert len(hist) == 1


def test_geofencing_marca_llegado_automatico(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
):
    from app.core.security import hash_password, create_access_token
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _vincular_tecnico_a_taller(db_session, None, taller, hash_password)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    # Incidente en exactamente la misma posicion que va a reportar el tecnico
    inc = incidente_factory(cliente, vehiculo, lat=-16.5000, lng=-68.1500)

    estado_aceptada = db_session.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc.id_incidente,
        id_taller=taller.id_taller,
        id_usuario=tecnico.id_usuario,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db_session.add(asig); db_session.commit(); db_session.refresh(asig)

    # Asegurar estado 'llegado' existe en catalogo
    if not db_session.query(EstadoAsignacion).filter_by(nombre="llegado").first():
        db_session.add(EstadoAsignacion(nombre="llegado"))
        db_session.commit()

    token = create_access_token(subject_id=tecnico.id_usuario, tipo="usuario")
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.5000, "longitud": -68.1500,  # exactamente en el incidente
            "id_asignacion": asig.id_asignacion,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["llegado_auto"] is True

    db_session.refresh(asig)
    assert asig.estado.nombre == "llegado"


def test_calcular_eta_funcion(monkeypatch):
    """Test unitario del helper de ETA con OSRM mockeado."""
    import asyncio
    from app.services import tracking_service

    # Forzar fallback al haversine (OSRM down)
    async def fake_failing_get(*args, **kwargs):
        raise Exception("OSRM down")
    monkeypatch.setattr("httpx.AsyncClient.get", fake_failing_get)

    d, eta = asyncio.run(tracking_service.calcular_eta(-16.5, -68.15, -16.6, -68.20))
    assert d > 0
    assert eta > 0
```

---

## Checklist de cierre F3
- [ ] Migración `0007` aplicada.
- [ ] Modelo `UbicacionTecnico` registrado.
- [ ] `POST /tecnicos/me/ubicacion` acepta pings y devuelve ETA.
- [ ] Histórico se inserta solo cuando hay `id_asignacion`.
- [ ] Geofencing 100m → estado pasa a "llegado" automáticamente.
- [ ] Cliente recibe evento `tecnico.posicion` por WS con la nueva pos + ETA.
- [ ] OSRM (público) responde; si falla, fallback haversine no rompe.
- [ ] Tests `tests/test_tracking.py` verdes (≥4).
- [ ] Flutter cliente: mapa con marker del técnico moviéndose.
- [ ] Flutter técnico: envío periódico cada 12s mientras viaje activo.

## Notas
- **Privacidad**: solo el cliente del incidente y el taller asignado deben ver la posición. La política `_can_subscribe` en F1 ya restringe `incidente:{id}` — robustecer si lo pruebas con un atacante.
- **Batería del técnico**: 12s es suficiente. Si quieren ahorrar más, subir a 20-30s y aceptar UX algo menos fluida.
- **OSRM público**: hay rate-limit. Para producción usar `osrm-backend` self-hosted en Docker, o pasar a Google Maps con key gratis.
- **Particionar `ubicacion_tecnico` por día**: si crece mucho, agregar Postgres partitioning. No es urgente para parcial.
- **Background tracking en iOS**: requiere capabilities especiales — solo demostrar en foreground.
