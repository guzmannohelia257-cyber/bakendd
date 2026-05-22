# F3 — Cancelación con compensación

> **Pre-requisito:** F1 (necesita `taller.id_tenant` y servicios declarados).
> **Independiente de F2.**
> **Esfuerzo:** 2 días.

## Objetivo (del enunciado)
> "El cliente confirmó un taller, pero su seguro respondió y llegará antes. El cliente puede cancelar un servicio confirmado. El taller que acudió debe recibir un **reconocimiento económico por el desplazamiento realizado**. Puede darse el caso de que ambos lleguen al mismo tiempo — el cliente elige quedarse con el seguro, pero el taller igual debe ser compensado."

Reglas de compensación que vamos a implementar:

| Estado de la asignación al cancelar | Compensación |
|---|---|
| `pendiente` (taller aún no aceptó) | **$0** — no hubo desplazamiento |
| `aceptada` (aceptó pero no salió) | **50% de la tarifa de traslado** del taller |
| `en_camino` o `llegado` (ya se desplazó) | **100% de la tarifa de traslado** |
| `completada` | **No se puede cancelar** (HTTP 409) |
| `cancelada` | **No se puede cancelar de nuevo** (HTTP 409) |

La tarifa de traslado vive en `taller.tarifa_traslado` (nueva columna). Default $5 si no la definió.

---

## Migración `0006_cancelacion`

```bash
.\venv\Scripts\alembic.exe revision -m "0006_cancelacion"
```

Contenido:

```python
"""0006_cancelacion

- Anade tarifa_traslado a taller (default 5.0).
- Anade columnas de cancelacion + compensacion a asignacion.
- Asegura que estado_asignacion tenga 'cancelada' y 'llegado'.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "REEMPLAZAR_POR_HASH"
down_revision: Union[str, None] = "REVISION_DE_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Tarifa de traslado por taller
    op.add_column(
        "taller",
        sa.Column("tarifa_traslado", sa.Numeric(10, 2), nullable=False, server_default="5.00"),
    )

    # 2) Campos de cancelacion en asignacion
    op.add_column("asignacion", sa.Column("cancelada_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("asignacion", sa.Column("motivo_cancelacion", sa.String(length=500), nullable=True))
    op.add_column("asignacion", sa.Column("cancelada_por", sa.String(length=20), nullable=True))  # 'cliente' | 'taller'
    op.add_column("asignacion", sa.Column("compensacion_monto", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "asignacion",
        sa.Column("compensacion_pagada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # 3) Asegurar catalogo
    for nombre in ("cancelada", "llegado"):
        op.execute(sa.text(
            "INSERT INTO estado_asignacion (nombre) VALUES (:n) ON CONFLICT DO NOTHING"
        ).bindparams(n=nombre))


def downgrade() -> None:
    op.drop_column("asignacion", "compensacion_pagada")
    op.drop_column("asignacion", "compensacion_monto")
    op.drop_column("asignacion", "cancelada_por")
    op.drop_column("asignacion", "motivo_cancelacion")
    op.drop_column("asignacion", "cancelada_at")
    op.drop_column("taller", "tarifa_traslado")
```

> Nota: `estado_asignacion` no tiene UNIQUE en `nombre` por defecto, pero el seed inicial probablemente sí los tiene. Si `ON CONFLICT DO NOTHING` falla por falta de constraint, cambiar a `SELECT ... INSERT WHERE NOT EXISTS`.

Aplicar: `alembic upgrade head`.

---

## Actualización de modelos

### `app/models/taller.py`

```python
class Taller(Base):
    # ... (existente)
    tarifa_traslado = Column(Numeric(10, 2), nullable=False, default=5.00)  # NUEVO
```

### `app/models/incidente.py`

```python
class Asignacion(Base):
    __tablename__ = "asignacion"

    # ... (existente)
    cancelada_at = Column(DateTime(timezone=True), nullable=True)
    motivo_cancelacion = Column(String(500), nullable=True)
    cancelada_por = Column(String(20), nullable=True)  # 'cliente' | 'taller'
    compensacion_monto = Column(Numeric(10, 2), nullable=True)
    compensacion_pagada = Column(Boolean, default=False, nullable=False)
```

Recordar `from sqlalchemy import String, Numeric, Boolean` ya están importados.

---

## Schemas `app/schemas/cancelacion_schema.py`

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class CancelarAsignacionRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


class CancelacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_asignacion: int
    id_taller: int
    cancelada_at: datetime
    cancelada_por: str
    motivo_cancelacion: str
    compensacion_monto: float
    compensacion_pagada: bool
    nuevo_estado: str  # nombre del estado_asignacion final


class TarifaTrasladoUpdate(BaseModel):
    tarifa_traslado: float = Field(..., ge=0, le=1000)
```

---

## Servicio `app/services/cancelacion_service.py`

```python
"""Logica de cancelacion con compensacion."""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalogos import EstadoAsignacion, EstadoPago, MetodoPago
from app.models.incidente import Asignacion, HistorialEstadoAsignacion
from app.models.taller import Taller
from app.models.transaccional import Pago
from app.models.usuario import Usuario


# Reglas de compensacion: % de la tarifa de traslado segun estado
COMPENSACION_POR_ESTADO = {
    "pendiente": Decimal("0.00"),
    "aceptada":  Decimal("0.50"),
    "en_camino": Decimal("1.00"),
    "llegado":   Decimal("1.00"),
}

ESTADOS_NO_CANCELABLES = {"completada", "cancelada"}


def cancelar_asignacion(
    db: Session,
    asignacion: Asignacion,
    usuario: Usuario,
    motivo: str,
) -> tuple[Asignacion, str]:
    """
    Cancela la asignacion y calcula compensacion. Retorna (asignacion, nuevo_estado_nombre).
    """
    # Validar dueno del incidente
    if asignacion.incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede cancelar")

    estado_actual = asignacion.estado.nombre
    if estado_actual in ESTADOS_NO_CANCELABLES:
        raise HTTPException(409, f"No se puede cancelar una asignacion '{estado_actual}'")

    factor = COMPENSACION_POR_ESTADO.get(estado_actual)
    if factor is None:
        raise HTTPException(500, f"Estado '{estado_actual}' sin regla de compensacion")

    # Calcular compensacion
    taller: Taller = asignacion.taller
    tarifa = Decimal(str(taller.tarifa_traslado or 0))
    compensacion = (tarifa * factor).quantize(Decimal("0.01"))

    # Estado destino
    estado_cancelada = (
        db.query(EstadoAsignacion).filter(EstadoAsignacion.nombre == "cancelada").first()
    )
    if not estado_cancelada:
        raise HTTPException(500, "Catalogo estado_asignacion sin 'cancelada'")

    # Registrar historial
    db.add(HistorialEstadoAsignacion(
        id_asignacion=asignacion.id_asignacion,
        id_estado_anterior=asignacion.id_estado_asignacion,
        id_estado_nuevo=estado_cancelada.id_estado_asignacion,
        observacion=f"Cancelado por cliente. Motivo: {motivo[:200]}",
    ))

    # Actualizar asignacion
    asignacion.id_estado_asignacion = estado_cancelada.id_estado_asignacion
    asignacion.cancelada_at = datetime.now(timezone.utc)
    asignacion.cancelada_por = "cliente"
    asignacion.motivo_cancelacion = motivo
    asignacion.compensacion_monto = compensacion
    asignacion.compensacion_pagada = (compensacion == 0)  # si es 0 ya "esta pagada"

    # Si hay compensacion > 0, crear Pago en estado pendiente
    if compensacion > 0:
        estado_pago_pendiente = (
            db.query(EstadoPago).filter(EstadoPago.nombre == "pendiente").first()
        )
        if not estado_pago_pendiente:
            # Fallback: tomar el primero
            estado_pago_pendiente = db.query(EstadoPago).first()

        metodo = db.query(MetodoPago).first()  # cualquier metodo por defecto

        if estado_pago_pendiente and metodo:
            # comision plataforma 10%, monto_taller 90%
            comision = (compensacion * Decimal("0.10")).quantize(Decimal("0.01"))
            monto_taller = (compensacion - comision).quantize(Decimal("0.01"))

            db.add(Pago(
                id_tenant=asignacion.id_tenant,
                id_incidente=asignacion.id_incidente,
                id_metodo_pago=metodo.id_metodo_pago,
                id_estado_pago=estado_pago_pendiente.id_estado_pago,
                monto_total=compensacion,
                comision_plataforma=comision,
                monto_taller=monto_taller,
                referencia_externa=f"compensacion-cancelacion-{asignacion.id_asignacion}",
            ))

    db.commit()
    db.refresh(asignacion)
    return asignacion, "cancelada"
```

---

## Endpoints

Agregar en `app/api/incidencias.py` (o donde estén las asignaciones — revisar primero):

```python
from app.schemas.cancelacion_schema import (
    CancelacionResponse,
    CancelarAsignacionRequest,
)
from app.services import cancelacion_service


@router.post(
    "/asignaciones/{id_asignacion}/cancelar",
    response_model=CancelacionResponse,
    summary="Cliente cancela una asignacion confirmada; calcula compensacion al taller",
)
def cancelar_asignacion_endpoint(
    id_asignacion: int,
    body: CancelarAsignacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.core.tenant_context import current_tenant
    # Cliente no tiene tenant -> bypass para localizar asignacion
    tok = current_tenant.set(0)
    try:
        asig = db.query(Asignacion).get(id_asignacion)
    finally:
        current_tenant.reset(tok)
    if not asig:
        raise HTTPException(404, "Asignacion no existe")

    asig_actualizada, nuevo_estado = cancelacion_service.cancelar_asignacion(
        db=db, asignacion=asig, usuario=current_user, motivo=body.motivo,
    )
    return CancelacionResponse(
        id_asignacion=asig_actualizada.id_asignacion,
        id_taller=asig_actualizada.id_taller,
        cancelada_at=asig_actualizada.cancelada_at,
        cancelada_por=asig_actualizada.cancelada_por,
        motivo_cancelacion=asig_actualizada.motivo_cancelacion,
        compensacion_monto=float(asig_actualizada.compensacion_monto or 0),
        compensacion_pagada=asig_actualizada.compensacion_pagada,
        nuevo_estado=nuevo_estado,
    )
```

Endpoint del taller para actualizar su tarifa de traslado (en `app/api/talleres.py`):

```python
from app.schemas.cancelacion_schema import TarifaTrasladoUpdate


@router.patch(
    "/mi-taller/tarifa-traslado",
    response_model=TallerResponse,
    summary="Actualizar mi tarifa de traslado (compensacion por cancelaciones)",
)
def actualizar_tarifa_traslado(
    body: TarifaTrasladoUpdate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    current_taller.tarifa_traslado = body.tarifa_traslado
    db.commit()
    db.refresh(current_taller)
    return current_taller
```

> `TallerResponse` debe incluir el nuevo campo `tarifa_traslado: float`. Agregarlo en el schema.

---

## Tests `tests/test_cancelacion.py`

```python
"""Tests de cancelacion con compensacion (F3)."""


def _crear_asignacion(db_session, tenant, taller, incidente, estado_nombre, tarifa_traslado=10):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    estado = db_session.query(EstadoAsignacion).filter_by(nombre=estado_nombre).first()
    if not estado:
        estado = EstadoAsignacion(nombre=estado_nombre)
        db_session.add(estado); db_session.commit(); db_session.refresh(estado)

    taller.tarifa_traslado = tarifa_traslado
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado.id_estado_asignacion,
    )
    db_session.add(asig); db_session.commit(); db_session.refresh(asig)
    return asig


def test_cancelar_pendiente_compensacion_cero(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers, incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "pendiente", tarifa_traslado=20)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Me ayudo un vecino"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["compensacion_monto"] == 0.0
    assert data["compensacion_pagada"] is True
    assert data["nuevo_estado"] == "cancelada"


def test_cancelar_aceptada_compensacion_50pct(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers, incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "aceptada", tarifa_traslado=20)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Llego el seguro"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    assert r.json()["compensacion_monto"] == 10.0  # 50% de 20


def test_cancelar_en_camino_compensacion_100pct(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers, incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "en_camino", tarifa_traslado=20)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Cambio de planes"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200
    assert r.json()["compensacion_monto"] == 20.0


def test_no_se_puede_cancelar_completada(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers, incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "completada")

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "X"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 409


def test_solo_dueno_puede_cancelar(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers, incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    dueno = cliente_factory()
    intruso = cliente_factory()
    vehiculo = vehiculo_factory(dueno)
    inc = incidente_factory(dueno, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "aceptada")

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Soy un atacante"},
        headers=cliente_auth_headers(intruso),
    )
    assert r.status_code == 403


def test_cancelacion_crea_pago_pendiente_de_compensacion(
    client, db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, cliente_auth_headers, incidente_factory,
):
    from app.models.transaccional import Pago

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "en_camino", tarifa_traslado=30)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "X"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200

    pago = db_session.query(Pago).filter_by(id_incidente=inc.id_incidente).first()
    assert pago is not None
    assert float(pago.monto_total) == 30.0
    assert float(pago.comision_plataforma) == 3.0  # 10%
    assert float(pago.monto_taller) == 27.0
```

> Estas pruebas usan los fixtures sugeridos en [F4_tests.md](./F4_tests.md). Si aún no existen, crearlos primero.

---

## Frontend
- **Mobile Flutter (cliente cancela)**: ver [G2MOBILE/M3_cancelar.md](../G2MOBILE/M3_cancelar.md)
- **Web Angular (panel compensaciones del taller)**: ver [G2WEB/W3_cancelacion.md](../G2WEB/W3_cancelacion.md)

---

## Checklist de cierre F3
- [ ] Migración `0006` aplicada.
- [ ] `taller.tarifa_traslado` defaults a 5.00.
- [ ] `POST /asignaciones/{id}/cancelar` calcula compensación correcta según estado.
- [ ] Estados no-cancelables responden 409.
- [ ] Solo el dueño del incidente puede cancelar (403 si no).
- [ ] Si compensación > 0, se crea `Pago` con `referencia_externa` indicativa.
- [ ] Tests `tests/test_cancelacion.py` verdes (≥6).
- [ ] Frontend muestra botón cancelar y modal de motivo.

## Notas / decisiones
- **¿Cliente bypassea filtro tenant?** Sí, igual que en cotización. El cliente final es público; no tiene tenant. Validamos manualmente que sea el dueño.
- **¿Por qué `Pago` y no una tabla aparte?** Reutilizamos el modelo existente — el `tipo` se distingue por `referencia_externa` que empieza con `compensacion-cancelacion-…`. Si se quiere robustecer, agregar columna `tipo` enum (`servicio`, `compensacion`, `propina`) en una migración futura.
- **¿Y si el taller cancela?** El enunciado solo habla del cliente cancelando. Si en el futuro un taller también puede cancelar, se reutiliza el mismo servicio cambiando `cancelada_por`.
- **Tarifa por defecto $5**: es un placeholder. Cada taller debe poner la suya en `PATCH /talleres/mi-taller/tarifa-traslado`.
