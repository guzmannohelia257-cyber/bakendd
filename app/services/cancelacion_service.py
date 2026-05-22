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


COMPENSACION_POR_ESTADO = {
    "pendiente": Decimal("0.00"),
    "aceptada": Decimal("0.50"),
    "en_camino": Decimal("1.00"),
    "llegado": Decimal("1.00"),
}

ESTADOS_NO_CANCELABLES = {"completada", "cancelada"}


def cancelar_asignacion(
    db: Session,
    asignacion: Asignacion,
    usuario: Usuario,
    motivo: str,
) -> tuple[Asignacion, str]:
    if asignacion.incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede cancelar")

    estado_actual = asignacion.estado.nombre
    if estado_actual in ESTADOS_NO_CANCELABLES:
        raise HTTPException(409, f"No se puede cancelar una asignacion '{estado_actual}'")

    factor = COMPENSACION_POR_ESTADO.get(estado_actual)
    if factor is None:
        raise HTTPException(500, f"Estado '{estado_actual}' sin regla de compensacion")

    taller: Taller = asignacion.taller
    tarifa = Decimal(str(taller.tarifa_traslado or 0))
    compensacion = (tarifa * factor).quantize(Decimal("0.01"))

    estado_cancelada = (
        db.query(EstadoAsignacion).filter(EstadoAsignacion.nombre == "cancelada").first()
    )
    if not estado_cancelada:
        raise HTTPException(500, "Catalogo estado_asignacion sin 'cancelada'")

    db.add(
        HistorialEstadoAsignacion(
            id_asignacion=asignacion.id_asignacion,
            id_estado_anterior=asignacion.id_estado_asignacion,
            id_estado_nuevo=estado_cancelada.id_estado_asignacion,
            observacion=f"Cancelado por cliente. Motivo: {motivo[:200]}",
        )
    )

    asignacion.id_estado_asignacion = estado_cancelada.id_estado_asignacion
    asignacion.cancelada_at = datetime.now(timezone.utc)
    asignacion.cancelada_por = "cliente"
    asignacion.motivo_cancelacion = motivo
    asignacion.compensacion_monto = compensacion
    asignacion.compensacion_pagada = compensacion == 0

    if compensacion > 0:
        estado_pago_pendiente = (
            db.query(EstadoPago).filter(EstadoPago.nombre == "pendiente").first()
        )
        if not estado_pago_pendiente:
            estado_pago_pendiente = db.query(EstadoPago).first()

        metodo = db.query(MetodoPago).first()

        if estado_pago_pendiente and metodo:
            comision = (compensacion * Decimal("0.10")).quantize(Decimal("0.01"))
            monto_taller = (compensacion - comision).quantize(Decimal("0.01"))

            db.add(
                Pago(
                    id_tenant=asignacion.id_tenant,
                    id_incidente=asignacion.id_incidente,
                    id_metodo_pago=metodo.id_metodo_pago,
                    id_estado_pago=estado_pago_pendiente.id_estado_pago,
                    monto_total=compensacion,
                    comision_plataforma=comision,
                    monto_taller=monto_taller,
                    referencia_externa=f"compensacion-cancelacion-{asignacion.id_asignacion}",
                )
            )

    db.commit()
    db.refresh(asignacion)
    return asignacion, "cancelada"
