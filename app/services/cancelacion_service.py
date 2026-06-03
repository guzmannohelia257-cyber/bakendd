"""Logica de cancelacion con compensacion."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalogos import EstadoAsignacion, EstadoPago, MetodoPago
from app.models.incidente import Asignacion, HistorialEstadoAsignacion
from app.models.tenant import Tenant
from app.models.transaccional import Pago
from app.models.usuario import Usuario


# Valor por defecto usado solo si el tenant no está cargado. Los porcentajes
# reales vienen de Tenant.pct_cancel_* y son configurables por el admin.
COMPENSACION_DEFAULT = {
    "pendiente": Decimal("0.00"),
    "aceptada": Decimal("0.50"),
    "en_camino": Decimal("1.00"),
    "llegado": Decimal("1.00"),
}

ESTADOS_NO_CANCELABLES = {"completada", "cancelada"}


def _factor_compensacion(tenant: Tenant | None, estado: str) -> Decimal | None:
    """Lee el porcentaje configurado en el tenant y lo convierte a factor.
    'llegado' usa el mismo porcentaje que 'en_camino'.
    """
    if estado not in COMPENSACION_DEFAULT:
        return None
    if tenant is None:
        return COMPENSACION_DEFAULT[estado]
    pct_map = {
        "pendiente": tenant.pct_cancel_pendiente,
        "aceptada": tenant.pct_cancel_aceptada,
        "en_camino": tenant.pct_cancel_en_camino,
        "llegado": tenant.pct_cancel_en_camino,
    }
    pct = pct_map.get(estado)
    if pct is None:
        return COMPENSACION_DEFAULT[estado]
    return (Decimal(str(pct)) / Decimal("100")).quantize(Decimal("0.01"))


def _marcado_en_camino_at(db: Session, asignacion: Asignacion) -> datetime | None:
    """Momento en que la asignacion paso a 'en_camino' (registro de historial).

    El ETA de la cotizacion empieza a correr cuando el tecnico marca 'en_camino',
    asi que ese instante es la base para calcular la hora de llegada prometida.
    Devuelve None si la asignacion aun no inicio viaje.
    """
    estado_en_camino = (
        db.query(EstadoAsignacion)
        .filter(EstadoAsignacion.nombre == "en_camino")
        .first()
    )
    if estado_en_camino is None:
        return None
    hist = (
        db.query(HistorialEstadoAsignacion)
        .filter(
            HistorialEstadoAsignacion.id_asignacion == asignacion.id_asignacion,
            HistorialEstadoAsignacion.id_estado_nuevo
            == estado_en_camino.id_estado_asignacion,
        )
        .order_by(HistorialEstadoAsignacion.created_at.desc())
        .first()
    )
    return hist.created_at if hist else None


def hora_limite_llegada_cotizacion(
    db: Session, asignacion: Asignacion
) -> datetime | None:
    """Hora limite de llegada prometida en la cotizacion (T1).

    T1 = momento 'en_camino' + eta_minutos. Es la hora a la que el tecnico
    deberia llegar segun la cotizacion. NO incluye la tolerancia del SLA.
    Devuelve None si aun no inicio viaje o la asignacion no tiene eta.
    """
    eta = asignacion.eta_minutos
    if not eta:
        return None
    en_camino_at = _marcado_en_camino_at(db, asignacion)
    if en_camino_at is None:
        return None
    return en_camino_at + timedelta(minutes=eta)


def tecnico_excedio_eta_cotizacion(db: Session, asignacion: Asignacion) -> bool:
    """True si el tecnico ya paso la hora de llegada prometida en la cotizacion (T1).

    Pasada esa hora el retraso es responsabilidad del taller, por lo que la
    cancelacion del cliente no se penaliza.
    """
    limite = hora_limite_llegada_cotizacion(db, asignacion)
    if limite is None:
        return False
    return datetime.now(timezone.utc) > limite


def cancelar_asignacion(
    db: Session,
    asignacion: Asignacion,
    usuario: Usuario,
    motivo: str,
) -> tuple[Asignacion, str, bool]:
    if asignacion.incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede cancelar")

    estado_actual = asignacion.estado.nombre
    if estado_actual in ESTADOS_NO_CANCELABLES:
        raise HTTPException(409, f"No se puede cancelar una asignacion '{estado_actual}'")

    # El tenant configura los porcentajes desde admin
    tenant = db.query(Tenant).filter_by(id_tenant=asignacion.id_tenant).first()
    factor = _factor_compensacion(tenant, estado_actual)
    if factor is None:
        raise HTTPException(500, f"Estado '{estado_actual}' sin regla de compensacion")

    # La compensacion es un porcentaje de la cotizacion que vio el cliente
    # (costo_estimado de la asignacion), no de una tarifa de traslado aparte.
    base = Decimal(str(asignacion.costo_estimado or 0))
    compensacion = (base * factor).quantize(Decimal("0.01"))

    # Excepcion: si el tecnico ya excedio la hora de llegada prometida en la
    # cotizacion (momento 'en_camino' + eta_minutos) y todavia va en camino, el
    # retraso es responsabilidad del taller: el cliente NO paga compensacion.
    sin_penalizacion_por_retraso = (
        estado_actual == "en_camino"
        and tecnico_excedio_eta_cotizacion(db, asignacion)
    )
    if sin_penalizacion_por_retraso:
        compensacion = Decimal("0.00")

    estado_cancelada = (
        db.query(EstadoAsignacion).filter(EstadoAsignacion.nombre == "cancelada").first()
    )
    if not estado_cancelada:
        raise HTTPException(500, "Catalogo estado_asignacion sin 'cancelada'")

    observacion = f"Cancelado por cliente. Motivo: {motivo[:200]}"
    if sin_penalizacion_por_retraso:
        observacion = (
            f"{observacion} | Sin compensacion: el tecnico excedio la hora de "
            "llegada de la cotizacion"
        )

    db.add(
        HistorialEstadoAsignacion(
            id_asignacion=asignacion.id_asignacion,
            id_estado_anterior=asignacion.id_estado_asignacion,
            id_estado_nuevo=estado_cancelada.id_estado_asignacion,
            observacion=observacion[:500],
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
    return asignacion, "cancelada", sin_penalizacion_por_retraso
