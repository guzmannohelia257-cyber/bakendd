"""
Estados de las cuatro maquinas de transicion del sistema:
  - estado_incidente   (4 estados)
  - estado_asignacion  (7 estados, incluye 'llegado' y 'cancelada')
  - estado_pago        (5 estados)
  - estado_cotizacion  (5 estados)
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.catalogos import (
    EstadoAsignacion,
    EstadoIncidente,
    EstadoPago,
)
from app.models.cotizacion import EstadoCotizacion
from SETT.config import (
    ESTADOS_ASIGNACION,
    ESTADOS_COTIZACION,
    ESTADOS_INCIDENTE,
    ESTADOS_PAGO,
)
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    db.add_all([EstadoIncidente(nombre=n, descripcion=d) for n, d in ESTADOS_INCIDENTE])
    db.add_all([EstadoAsignacion(nombre=n) for n in ESTADOS_ASIGNACION])
    db.add_all([EstadoPago(nombre=n) for n in ESTADOS_PAGO])
    db.add_all([EstadoCotizacion(nombre=n) for n in ESTADOS_COTIZACION])
    db.commit()

    for e in db.query(EstadoIncidente).all():
        ctx.estado_incidente[e.nombre] = e
    for e in db.query(EstadoAsignacion).all():
        ctx.estado_asignacion[e.nombre] = e
    for e in db.query(EstadoPago).all():
        ctx.estado_pago[e.nombre] = e
    for e in db.query(EstadoCotizacion).all():
        ctx.estado_cotizacion[e.nombre] = e

    logger.info(
        f"[catalogos] estados: incidente={len(ctx.estado_incidente)}, "
        f"asignacion={len(ctx.estado_asignacion)}, "
        f"pago={len(ctx.estado_pago)}, "
        f"cotizacion={len(ctx.estado_cotizacion)}"
    )
