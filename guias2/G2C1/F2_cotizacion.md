# F2 — Cotización (≥2-3 talleres comparativos)

> **Pre-requisito:** F1 completado (necesita `codigo` y `requiere_cotizacion` en `categoria_problema`, y `tarifa_base` en `taller_servicio`).
> **Esfuerzo:** 3 días.

## Objetivo (del enunciado)
Cuando el incidente del cliente pertenece a una **categoría que `requiere_cotizacion=true`** (chapería, mecánica general, eléctrico, electrónico), el cliente puede:

1. Pedir cotización a los 3 talleres compatibles más cercanos.
2. Los talleres reciben la solicitud y responden con: monto del servicio, monto de repuestos, garantía (días), nota.
3. El cliente ve las respuestas en una pantalla comparativa.
4. Al aceptar una, se crea automáticamente la `Asignacion` y las otras quedan **rechazadas**.

Regla del enunciado: "el cliente debe poder recibir **al menos 2 o 3 cotizaciones** comparativas".

---

## Modelo de datos

### Migración `0005_cotizacion`

```bash
.\venv\Scripts\alembic.exe revision -m "0005_cotizacion"
```

Contenido:

```python
"""0005_cotizacion

Crea catalogo estado_cotizacion + tabla cotizacion (tenant-scoped).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "REEMPLAZAR_POR_HASH"
down_revision: Union[str, None] = "REVISION_DE_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ESTADOS = ["pendiente", "enviada", "aceptada", "rechazada", "expirada"]


def upgrade() -> None:
    op.create_table(
        "estado_cotizacion",
        sa.Column("id_estado_cotizacion", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=50), nullable=False, unique=True),
    )
    for nombre in ESTADOS:
        op.execute(sa.text(
            "INSERT INTO estado_cotizacion (nombre) VALUES (:n) ON CONFLICT DO NOTHING"
        ).bindparams(n=nombre))

    op.create_table(
        "cotizacion",
        sa.Column("id_cotizacion", sa.Integer(), primary_key=True),
        sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=False, index=True),
        sa.Column("id_incidente", sa.Integer(), sa.ForeignKey("incidente.id_incidente"), nullable=False, index=True),
        sa.Column("id_taller", sa.Integer(), sa.ForeignKey("taller.id_taller"), nullable=False, index=True),
        sa.Column("id_estado_cotizacion", sa.Integer(), sa.ForeignKey("estado_cotizacion.id_estado_cotizacion"), nullable=False),
        sa.Column("monto_servicio", sa.Numeric(10, 2), nullable=True),
        sa.Column("monto_repuestos", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("garantia_dias", sa.Integer(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("validez_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("id_incidente", "id_taller", name="uq_cotizacion_incidente_taller"),
    )


def downgrade() -> None:
    op.drop_table("cotizacion")
    op.drop_table("estado_cotizacion")
```

Aplicar: `alembic upgrade head`.

### Modelo `app/models/cotizacion.py` (nuevo)

```python
"""Cotizaciones: ofertas economicas que un taller envia al cliente
antes de aceptar un incidente, cuando la categoria requiere negociacion previa.
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class EstadoCotizacion(Base):
    __tablename__ = "estado_cotizacion"

    id_estado_cotizacion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)


class Cotizacion(Base):
    __tablename__ = "cotizacion"
    __table_args__ = (
        UniqueConstraint("id_incidente", "id_taller", name="uq_cotizacion_incidente_taller"),
    )

    id_cotizacion = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    id_estado_cotizacion = Column(Integer, ForeignKey("estado_cotizacion.id_estado_cotizacion"), nullable=False)

    monto_servicio = Column(Numeric(10, 2), nullable=True)
    monto_repuestos = Column(Numeric(10, 2), nullable=True, default=0)
    garantia_dias = Column(Integer, nullable=True)
    nota = Column(Text, nullable=True)
    validez_hasta = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    incidente = relationship("Incidente")
    taller = relationship("Taller")
    estado = relationship("EstadoCotizacion")

    @property
    def monto_total(self):
        s = self.monto_servicio or 0
        r = self.monto_repuestos or 0
        return float(s) + float(r)
```

Registrar en `app/models/__init__.py`:

```python
from app.models.cotizacion import Cotizacion, EstadoCotizacion
# ... agregar a __all__
```

---

## Schemas `app/schemas/cotizacion_schema.py`

```python
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class SolicitarCotizacionesRequest(BaseModel):
    """Cliente pide cotizaciones para un incidente a top-N talleres."""
    radio_km: float = Field(20.0, gt=0, le=100)
    max_talleres: int = Field(3, ge=2, le=5, description="Numero de talleres a invitar")
    validez_horas: int = Field(2, ge=1, le=24, description="Tiempo de validez de las cotizaciones")


class ResponderCotizacionRequest(BaseModel):
    """Taller responde una cotizacion pendiente."""
    monto_servicio: float = Field(..., ge=0)
    monto_repuestos: float = Field(0, ge=0)
    garantia_dias: Optional[int] = Field(None, ge=0, le=365)
    nota: Optional[str] = Field(None, max_length=1000)


class TallerMiniC(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_taller: int
    nombre: str
    telefono: Optional[str] = None


class EstadoCotizacionMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_estado_cotizacion: int
    nombre: str


class CotizacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cotizacion: int
    id_incidente: int
    id_taller: int
    id_estado_cotizacion: int
    monto_servicio: Optional[float] = None
    monto_repuestos: Optional[float] = None
    garantia_dias: Optional[int] = None
    nota: Optional[str] = None
    validez_hasta: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    taller: Optional[TallerMiniC] = None
    estado: Optional[EstadoCotizacionMini] = None

    @property
    def monto_total(self) -> Optional[float]:
        if self.monto_servicio is None:
            return None
        return float(self.monto_servicio) + float(self.monto_repuestos or 0)


class CotizacionesSolicitadasResponse(BaseModel):
    id_incidente: int
    invitadas: int
    cotizaciones: List[CotizacionResponse]
```

---

## Servicio de negocio `app/services/cotizacion_service.py`

```python
"""Logica de negocio de cotizaciones."""
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalogos import CategoriaProblema, EstadoAsignacion
from app.models.cotizacion import Cotizacion, EstadoCotizacion
from app.models.incidente import Asignacion, Incidente
from app.models.taller import Taller, TallerServicio
from app.models.usuario import Usuario


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return 2 * R * asin(sqrt(a))


def _get_estado(db: Session, nombre: str) -> EstadoCotizacion:
    estado = db.query(EstadoCotizacion).filter(EstadoCotizacion.nombre == nombre).first()
    if not estado:
        raise HTTPException(500, f"Catalogo estado_cotizacion sin '{nombre}'")
    return estado


def solicitar_cotizaciones(
    db: Session,
    incidente: Incidente,
    usuario: Usuario,
    radio_km: float = 20.0,
    max_talleres: int = 3,
    validez_horas: int = 2,
) -> list[Cotizacion]:
    """
    Verifica que la categoria requiera cotizacion. Selecciona top-N talleres
    compatibles por cercania. Crea Cotizaciones en estado 'pendiente'.
    """
    if incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede pedir cotizaciones")

    if incidente.id_categoria is None:
        raise HTTPException(400, "El incidente aun no tiene categoria clasificada")

    categoria = db.query(CategoriaProblema).get(incidente.id_categoria)
    if not categoria:
        raise HTTPException(400, "Categoria invalida")
    if not categoria.requiere_cotizacion:
        raise HTTPException(
            400,
            f"La categoria '{categoria.codigo}' no requiere cotizacion: el servicio se solicita directo"
        )

    # Talleres compatibles (similar a /talleres/compatibles pero aplicado a este incidente)
    candidatos = (
        db.query(Taller, TallerServicio)
        .join(TallerServicio, TallerServicio.id_taller == Taller.id_taller)
        .filter(
            TallerServicio.id_categoria == incidente.id_categoria,
            Taller.activo == True,            # noqa: E712
            Taller.disponible == True,        # noqa: E712
            Taller.latitud.isnot(None),
            Taller.longitud.isnot(None),
        )
        .all()
    )

    con_distancia = []
    for taller, _servicio in candidatos:
        d = _haversine_km(incidente.latitud, incidente.longitud, taller.latitud, taller.longitud)
        if d <= radio_km:
            con_distancia.append((d, taller))
    con_distancia.sort(key=lambda x: x[0])

    seleccionados = [t for _d, t in con_distancia[:max_talleres]]
    if len(seleccionados) < 2:
        raise HTTPException(
            422,
            f"No hay suficientes talleres compatibles (encontrados: {len(seleccionados)}, minimo: 2). "
            "Amplia el radio o intenta de nuevo."
        )

    # No crear duplicados: si ya hay cotizaciones para este incidente, fallar
    ya_solicitado = db.query(Cotizacion).filter(Cotizacion.id_incidente == incidente.id_incidente).first()
    if ya_solicitado:
        raise HTTPException(409, "Ya solicitaste cotizaciones para este incidente")

    pendiente = _get_estado(db, "pendiente")
    validez = datetime.now(timezone.utc) + timedelta(hours=validez_horas)

    creadas = []
    for taller in seleccionados:
        cot = Cotizacion(
            id_tenant=taller.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_estado_cotizacion=pendiente.id_estado_cotizacion,
            validez_hasta=validez,
        )
        db.add(cot)
        creadas.append(cot)

    db.commit()
    for c in creadas:
        db.refresh(c)

    # TODO: notificar push a cada taller (F2.5). Por ahora no bloquea.
    return creadas


def responder_cotizacion(
    db: Session,
    cotizacion: Cotizacion,
    taller: Taller,
    monto_servicio: float,
    monto_repuestos: float,
    garantia_dias: int | None,
    nota: str | None,
) -> Cotizacion:
    if cotizacion.id_taller != taller.id_taller:
        raise HTTPException(403, "Esta cotizacion no te pertenece")
    if cotizacion.estado.nombre not in ("pendiente",):
        raise HTTPException(409, f"No puedes responder una cotizacion en estado '{cotizacion.estado.nombre}'")
    if cotizacion.validez_hasta and cotizacion.validez_hasta < datetime.now(timezone.utc):
        _marcar_expirada(db, cotizacion)
        raise HTTPException(410, "Esta cotizacion ya expiro")

    cotizacion.monto_servicio = monto_servicio
    cotizacion.monto_repuestos = monto_repuestos
    cotizacion.garantia_dias = garantia_dias
    cotizacion.nota = nota
    cotizacion.id_estado_cotizacion = _get_estado(db, "enviada").id_estado_cotizacion
    db.commit()
    db.refresh(cotizacion)
    return cotizacion


def aceptar_cotizacion(
    db: Session,
    cotizacion: Cotizacion,
    usuario: Usuario,
) -> Asignacion:
    """
    Cliente acepta una cotizacion. Crea Asignacion. Las otras cotizaciones del
    mismo incidente pasan a 'rechazada'.
    """
    incidente = db.query(Incidente).get(cotizacion.id_incidente)
    if incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede aceptar cotizaciones")

    if cotizacion.estado.nombre != "enviada":
        raise HTTPException(409, f"No puedes aceptar una cotizacion en estado '{cotizacion.estado.nombre}'")

    # 1) Aceptar la elegida
    cotizacion.id_estado_cotizacion = _get_estado(db, "aceptada").id_estado_cotizacion

    # 2) Rechazar todas las demas del mismo incidente
    otras = (
        db.query(Cotizacion)
        .filter(
            Cotizacion.id_incidente == cotizacion.id_incidente,
            Cotizacion.id_cotizacion != cotizacion.id_cotizacion,
        )
        .all()
    )
    estado_rechazada = _get_estado(db, "rechazada")
    for o in otras:
        if o.estado.nombre in ("pendiente", "enviada"):
            o.id_estado_cotizacion = estado_rechazada.id_estado_cotizacion

    # 3) Crear Asignacion (estado 'aceptada')
    estado_asig_aceptada = (
        db.query(EstadoAsignacion).filter(EstadoAsignacion.nombre == "aceptada").first()
    )
    if not estado_asig_aceptada:
        raise HTTPException(500, "Catalogo estado_asignacion sin 'aceptada'")

    asig = Asignacion(
        id_tenant=cotizacion.id_tenant,
        id_incidente=cotizacion.id_incidente,
        id_taller=cotizacion.id_taller,
        id_estado_asignacion=estado_asig_aceptada.id_estado_asignacion,
        costo_estimado=cotizacion.monto_total,
        nota_taller=cotizacion.nota,
    )
    db.add(asig)
    db.commit()
    db.refresh(asig)
    return asig


def _marcar_expirada(db: Session, cot: Cotizacion) -> None:
    cot.id_estado_cotizacion = _get_estado(db, "expirada").id_estado_cotizacion
    db.commit()
```

---

## Endpoints `app/api/cotizaciones.py`

```python
"""Endpoints de cotizaciones."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_taller, get_current_user
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.cotizacion import Cotizacion
from app.models.incidente import Incidente
from app.models.taller import Taller
from app.models.usuario import Usuario
from app.schemas.cotizacion_schema import (
    CotizacionResponse,
    CotizacionesSolicitadasResponse,
    ResponderCotizacionRequest,
    SolicitarCotizacionesRequest,
)
from app.services import cotizacion_service


router = APIRouter(tags=["Cotizaciones"])


# ============ CLIENTE ============

@router.post(
    "/incidentes/{id_incidente}/cotizaciones/solicitar",
    response_model=CotizacionesSolicitadasResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cliente solicita cotizaciones a top-N talleres",
)
def solicitar(
    id_incidente: int,
    body: SolicitarCotizacionesRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.query(Incidente).get(id_incidente)
    if not incidente:
        raise HTTPException(404, "Incidente no existe")

    creadas = cotizacion_service.solicitar_cotizaciones(
        db=db,
        incidente=incidente,
        usuario=current_user,
        radio_km=body.radio_km,
        max_talleres=body.max_talleres,
        validez_horas=body.validez_horas,
    )
    return CotizacionesSolicitadasResponse(
        id_incidente=id_incidente,
        invitadas=len(creadas),
        cotizaciones=creadas,
    )


@router.get(
    "/incidentes/{id_incidente}/cotizaciones",
    response_model=List[CotizacionResponse],
    summary="Listar cotizaciones que el cliente recibio para su incidente",
)
def listar_cotizaciones_cliente(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.query(Incidente).get(id_incidente)
    if not incidente:
        raise HTTPException(404, "Incidente no existe")
    if incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede verlas")
    # Endpoint del cliente: bypass del filtro tenant (las cotizaciones son de
    # varios tenants distintos) usando tid=0.
    tok = current_tenant.set(0)
    try:
        return (
            db.query(Cotizacion)
            .filter(Cotizacion.id_incidente == id_incidente)
            .order_by(Cotizacion.created_at.desc())
            .all()
        )
    finally:
        current_tenant.reset(tok)


@router.post(
    "/cotizaciones/{id_cotizacion}/aceptar",
    summary="Cliente acepta una cotizacion; crea Asignacion y rechaza las otras",
)
def aceptar(
    id_cotizacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    tok = current_tenant.set(0)
    try:
        cot = db.query(Cotizacion).get(id_cotizacion)
    finally:
        current_tenant.reset(tok)
    if not cot:
        raise HTTPException(404, "Cotizacion no existe")
    asig = cotizacion_service.aceptar_cotizacion(db, cot, current_user)
    return {"id_asignacion": asig.id_asignacion, "id_taller": asig.id_taller}


# ============ TALLER ============

@router.get(
    "/talleres/mi-taller/cotizaciones",
    response_model=List[CotizacionResponse],
    summary="Bandeja de cotizaciones del taller autenticado",
)
def bandeja_taller(
    db: Session = Depends(get_db),
    estado: str | None = None,
    current_taller: Taller = Depends(get_current_taller),
):
    q = db.query(Cotizacion).filter(Cotizacion.id_taller == current_taller.id_taller)
    if estado:
        from app.models.cotizacion import EstadoCotizacion
        ec = db.query(EstadoCotizacion).filter(EstadoCotizacion.nombre == estado).first()
        if not ec:
            raise HTTPException(400, f"Estado '{estado}' invalido")
        q = q.filter(Cotizacion.id_estado_cotizacion == ec.id_estado_cotizacion)
    return q.order_by(Cotizacion.created_at.desc()).all()


@router.post(
    "/cotizaciones/{id_cotizacion}/responder",
    response_model=CotizacionResponse,
    summary="Taller responde una cotizacion pendiente",
)
def responder(
    id_cotizacion: int,
    body: ResponderCotizacionRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    cot = db.query(Cotizacion).get(id_cotizacion)
    if not cot:
        raise HTTPException(404, "Cotizacion no existe")
    return cotizacion_service.responder_cotizacion(
        db=db,
        cotizacion=cot,
        taller=current_taller,
        monto_servicio=body.monto_servicio,
        monto_repuestos=body.monto_repuestos,
        garantia_dias=body.garantia_dias,
        nota=body.nota,
    )
```

Registrar en `app/api/__init__.py` y `app/main.py` como los otros routers.

---

## Frontend
- **Mobile Flutter (cliente)**: ver [G2MOBILE/M2_cotizacion.md](../G2MOBILE/M2_cotizacion.md)
- **Web Angular (taller)**: ver [G2WEB/W2_cotizacion.md](../G2WEB/W2_cotizacion.md)

---

## Tests (más en F4)

`tests/test_cotizaciones.py`:

```python
"""Tests del flujo de cotizacion (F2)."""
import uuid
from datetime import datetime, timezone, timedelta


def _crear_incidente_categoria(db_session, usuario, vehiculo, categoria, lat=-16.5, lng=-68.15):
    from app.models.catalogos import EstadoIncidente
    from app.models.incidente import Incidente

    estado = db_session.query(EstadoIncidente).first()
    inc = Incidente(
        id_usuario=usuario.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=estado.id_estado,
        id_categoria=categoria.id_categoria,
        latitud=lat,
        longitud=lng,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc


def test_solicitar_cotizaciones_invita_a_3_talleres(
    client, db_session, tenant_factory, taller_factory, cliente_factory, vehiculo_factory, cliente_auth_headers
):
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    # 3 talleres en la misma zona, todos con chaperia
    talleres = []
    for _ in range(3):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        talleres.append(taller)
        db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria, tarifa_base=200))
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    headers = cliente_auth_headers(cliente)
    r = client.post(
        f"/incidentes/{incidente.id_incidente}/cotizaciones/solicitar",
        json={"radio_km": 50, "max_talleres": 3, "validez_horas": 2},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["invitadas"] == 3
    assert len(data["cotizaciones"]) == 3


def test_no_cotizar_categoria_directa(
    client, db_session, cliente_factory, vehiculo_factory, cliente_auth_headers
):
    """Categoria 'llantas' no requiere cotizacion -> 400."""
    from app.models.catalogos import CategoriaProblema
    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    headers = cliente_auth_headers(cliente)
    r = client.post(
        f"/incidentes/{incidente.id_incidente}/cotizaciones/solicitar",
        json={"radio_km": 50, "max_talleres": 3, "validez_horas": 2},
        headers=headers,
    )
    assert r.status_code == 400


def test_taller_responde_cotizacion(
    client, db_session, tenant_factory, taller_factory, taller_auth_headers,
    cliente_factory, vehiculo_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()
    pendiente = db_session.query(EstadoCotizacion).filter_by(nombre="pendiente").one()

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    cot = Cotizacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_cotizacion=pendiente.id_estado_cotizacion,
    )
    db_session.add(cot)
    db_session.commit()
    db_session.refresh(cot)

    headers = taller_auth_headers(taller)
    r = client.post(
        f"/cotizaciones/{cot.id_cotizacion}/responder",
        json={"monto_servicio": 500, "monto_repuestos": 200, "garantia_dias": 30, "nota": "Incluye lijado"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["monto_servicio"] == 500
    assert data["monto_repuestos"] == 200


def test_aceptar_cotizacion_rechaza_otras_y_crea_asignacion(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers,
):
    from app.models.catalogos import CategoriaProblema, EstadoAsignacion
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.incidente import Asignacion

    cat = db_session.query(CategoriaProblema).filter_by(codigo="mecanica_general").one()
    enviada = db_session.query(EstadoCotizacion).filter_by(nombre="enviada").one()

    # 2 talleres con cotizaciones enviadas
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    cots = []
    for _ in range(2):
        t = tenant_factory()
        taller = taller_factory(t)
        cot = Cotizacion(
            id_tenant=t.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_estado_cotizacion=enviada.id_estado_cotizacion,
            monto_servicio=300, monto_repuestos=100, garantia_dias=15,
        )
        db_session.add(cot); cots.append(cot)
    db_session.commit()
    for c in cots: db_session.refresh(c)

    headers = cliente_auth_headers(cliente)
    elegida = cots[0]
    r = client.post(f"/cotizaciones/{elegida.id_cotizacion}/aceptar", headers=headers)
    assert r.status_code == 200, r.text

    # Recargar estados
    db_session.refresh(elegida)
    db_session.refresh(cots[1])
    assert elegida.estado.nombre == "aceptada"
    assert cots[1].estado.nombre == "rechazada"

    asig = db_session.query(Asignacion).filter_by(id_incidente=incidente.id_incidente).first()
    assert asig is not None
    assert asig.id_taller == elegida.id_taller
```

> Estas pruebas usan fixtures `cliente_factory`, `vehiculo_factory`, `cliente_auth_headers` que aún no existen. **Agregar en `conftest.py`** (ver fixtures sugeridas en [F4_tests.md](./F4_tests.md)).

---

## Checklist de cierre F2
- [ ] Migración `0005` aplicada.
- [ ] `POST /incidentes/{id}/cotizaciones/solicitar` falla con 400 si categoría no requiere cotización.
- [ ] Si hay ≥2 talleres compatibles, crea N cotizaciones en estado `pendiente`.
- [ ] `POST /cotizaciones/{id}/responder` solo lo puede usar el taller dueño.
- [ ] `POST /cotizaciones/{id}/aceptar` crea `Asignacion` + rechaza las hermanas.
- [ ] Bandejas funcionando para taller y cliente.
- [ ] Tests `tests/test_cotizaciones.py` verdes (≥6).
- [ ] Flutter: pantalla de comparación lista al menos las cotizaciones recibidas.
- [ ] Angular: bandeja del taller con form modal de respuesta.

## Notas / decisiones
- **¿Por qué cliente bypasea el filtro tenant?** Las cotizaciones del cliente vienen de varios tenants distintos. El usuario es público y no tiene tenant propio, así que `current_tenant.get()` es None y el filtro no se aplica. Pero por seguridad reforzamos verificando `incidente.id_usuario == current_user.id_usuario`.
- **¿Por qué no hay `precio_total` calculado?** Está como `@property` en el modelo (no en BD) porque las dos columnas pueden ser nulas en `pendiente`. El frontend lo calcula al mostrar.
- **Expiración**: por simplicidad, marcamos expirada al intentar usarla. Un cron que las marque periódicamente queda para Ciclo 2/3.
