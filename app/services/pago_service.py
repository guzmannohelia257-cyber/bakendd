"""
Servicio de Pagos extendido (segundo parcial):
  - estimar_costo: estimacion referencial con tarifas del catalogo + categoria IA
  - preautorizar: PaymentIntent con capture_method=manual
  - capturar: captura el intent con el monto final cuando el servicio termina
  - penalizar: cobro fijo cuando el cliente cancela con tecnico en_camino
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import stripe
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalogos import EstadoAsignacion, EstadoPago, MetodoPago
from app.models.configuracion import ConfiguracionPlataforma
from app.models.cotizacion import Cotizacion, EstadoCotizacion
from app.models.incidente import Asignacion, HistorialEstadoAsignacion, Incidente
from app.models.taller import Taller, TallerServicio
from app.models.transaccional import Pago


PENALIZACION_FIJA_USD = Decimal("5.00")
SLA_PENALIZACION_DEFAULT_PCT = 15
SLA_TOLERANCIA_DEFAULT_MIN = 20
ESTIMACION_FALLBACK_USD = Decimal("20.00")
ESTIMACION_HISTORICO_DIAS = 90
ESTIMACION_HISTORICO_MINIMO = 3


def get_configuracion(db: Session) -> ConfiguracionPlataforma:
    """Devuelve la configuracion global singleton de la plataforma.

    Si la fila no existe (p. ej. tras un reseed que hace TRUNCATE) la crea con
    los valores por defecto (penalizacion 15%, tolerancia 20 min) y hace flush.
    No hace commit: la transaccion la cierra quien invoca.
    """
    config = (
        db.query(ConfiguracionPlataforma)
        .order_by(ConfiguracionPlataforma.id.asc())
        .first()
    )
    if config is None:
        config = ConfiguracionPlataforma(
            sla_penalizacion_pct=SLA_PENALIZACION_DEFAULT_PCT,
            sla_tolerancia_min=SLA_TOLERANCIA_DEFAULT_MIN,
        )
        db.add(config)
        db.flush()
    return config


def _estado_pago_id(db: Session, nombre: str) -> int:
    est = db.query(EstadoPago).filter_by(nombre=nombre).first()
    if not est:
        raise HTTPException(500, f"Catalogo estado_pago sin '{nombre}'")
    return est.id_estado_pago


def _metodo_default(db: Session) -> int:
    m = db.query(MetodoPago).order_by(MetodoPago.id_metodo_pago.asc()).first()
    if not m:
        raise HTTPException(500, "Catalogo metodo_pago vacio")
    return m.id_metodo_pago


def estimar_costo(db: Session, incidente: Incidente) -> Decimal:
    """
    Estima el costo referencial. Prioridad:
      1. Promedio de cotizaciones ACEPTADAS de la misma categoria en los
         ultimos 90 dias (aprendizaje de trabajos reales). Solo si hay >= 3.
      2. Promedio de tarifa_base entre talleres que ofrecen esa categoria.
      3. Fallback de USD 20.
    """
    if not incidente.id_categoria:
        return ESTIMACION_FALLBACK_USD

    # 1. Histórico de cotizaciones aceptadas
    desde = datetime.now(timezone.utc) - timedelta(days=ESTIMACION_HISTORICO_DIAS)
    hist_query = (
        db.query(
            func.count(Cotizacion.id_cotizacion),
            func.avg(
                func.coalesce(Cotizacion.monto_servicio, 0)
                + func.coalesce(Cotizacion.monto_repuestos, 0)
                + func.coalesce(Cotizacion.monto_traslado, 0)
            ),
        )
        .join(Incidente, Incidente.id_incidente == Cotizacion.id_incidente)
        .join(EstadoCotizacion, EstadoCotizacion.id_estado_cotizacion == Cotizacion.id_estado_cotizacion)
        .filter(
            Incidente.id_categoria == incidente.id_categoria,
            EstadoCotizacion.nombre == "aceptada",
            Cotizacion.created_at >= desde,
        )
    )
    n_hist, prom_hist = hist_query.one()
    if n_hist and n_hist >= ESTIMACION_HISTORICO_MINIMO and prom_hist:
        return Decimal(str(prom_hist)).quantize(Decimal("0.01"))

    # 2. Promedio de tarifa_base de talleres
    tarifas = (
        db.query(TallerServicio.tarifa_base)
        .filter(
            TallerServicio.id_categoria == incidente.id_categoria,
            TallerServicio.tarifa_base.isnot(None),
        )
        .all()
    )
    valores = [Decimal(str(t[0])) for t in tarifas if t[0] is not None]
    if not valores:
        return ESTIMACION_FALLBACK_USD

    promedio = sum(valores) / Decimal(len(valores))
    return promedio.quantize(Decimal("0.01"))


def _load_stripe():
    s = get_settings()
    if not s.STRIPE_SECRET_KEY:
        raise HTTPException(500, "Falta STRIPE_SECRET_KEY en .env")
    stripe.api_key = s.STRIPE_SECRET_KEY


def preautorizar(
    db: Session,
    incidente: Incidente,
    monto: Decimal,
) -> dict:
    """
    Crea (o reusa) un PaymentIntent en modo manual_capture. NO cobra
    todavia, solo reserva el monto en la tarjeta del cliente.
    """
    _load_stripe()
    monto_centavos = int(monto * 100)

    intent = stripe.PaymentIntent.create(
        amount=monto_centavos,
        currency="usd",
        capture_method="manual",
        automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        metadata={
            "id_incidente": str(incidente.id_incidente),
            "id_usuario": str(incidente.id_usuario),
            "tipo": "preauth",
        },
    )

    incidente.monto_preautorizacion = monto
    incidente.stripe_preauth_id = intent["id"]

    # Persistir un Pago de tipo "preauth" para trazabilidad.
    pago = (
        db.query(Pago)
        .filter(
            Pago.id_incidente == incidente.id_incidente,
            Pago.tipo == "preauth",
        )
        .first()
    )
    estado_pendiente = _estado_pago_id(db, "pendiente")
    if pago:
        pago.referencia_externa = intent["id"]
        pago.monto_total = monto
        pago.id_estado_pago = estado_pendiente
    else:
        pago = Pago(
            id_tenant=incidente.id_tenant,
            id_incidente=incidente.id_incidente,
            id_metodo_pago=_metodo_default(db),
            id_estado_pago=estado_pendiente,
            tipo="preauth",
            monto_total=monto,
            comision_plataforma=Decimal("0.00"),
            monto_taller=monto,
            referencia_externa=intent["id"],
        )
        db.add(pago)

    db.commit()
    db.refresh(incidente)

    return {
        "client_secret": intent.get("client_secret"),
        "payment_intent_id": intent["id"],
        "monto_centavos": monto_centavos,
        "monto_usd": float(monto),
    }


def capturar(
    db: Session,
    incidente: Incidente,
    monto_final: Optional[Decimal] = None,
) -> Pago:
    """
    Captura el PaymentIntent en modo manual. Si monto_final < pre-autorizado,
    Stripe libera la diferencia automaticamente. Si monto_final > pre-autorizado
    devolvemos 409 (debe pedirse una adenda primero).
    """
    if not incidente.stripe_preauth_id:
        raise HTTPException(409, "Este incidente no tiene pre-autorizacion activa")

    _load_stripe()
    preauth = Decimal(str(incidente.monto_preautorizacion or 0))
    monto = monto_final if monto_final is not None else preauth
    if monto <= 0:
        raise HTTPException(400, "El monto a capturar debe ser positivo")
    if monto > preauth:
        raise HTTPException(
            409,
            f"Monto ({monto}) excede la pre-autorizacion ({preauth}). "
            "Registra una adenda primero.",
        )

    monto_centavos = int(monto * 100)
    try:
        captured = stripe.PaymentIntent.capture(
            incidente.stripe_preauth_id,
            amount_to_capture=monto_centavos,
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(
            502,
            f"Error capturando pago en Stripe: {getattr(exc, 'user_message', str(exc))}",
        )

    # Crear el Pago de tipo 'servicio' con el monto final capturado.
    comision = (monto * Decimal("0.10")).quantize(Decimal("0.01"))
    pago = Pago(
        id_tenant=incidente.id_tenant,
        id_incidente=incidente.id_incidente,
        id_metodo_pago=_metodo_default(db),
        id_estado_pago=_estado_pago_id(db, "completado"),
        tipo="servicio",
        monto_total=monto,
        comision_plataforma=comision,
        monto_taller=monto - comision,
        referencia_externa=captured["id"],
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


def penalizar_por_cancelacion(
    db: Session,
    incidente: Incidente,
    monto: Decimal = PENALIZACION_FIJA_USD,
) -> Pago:
    """
    Cobro fijo cuando el cliente cancela un incidente cuyo tecnico ya esta en
    camino. Se registra como Pago tipo='penalizacion' en estado 'pendiente'
    (el cobro real puede dispararse via Stripe si hay PaymentIntent de
    preauth disponible).
    """
    pago = Pago(
        id_tenant=incidente.id_tenant,
        id_incidente=incidente.id_incidente,
        id_metodo_pago=_metodo_default(db),
        id_estado_pago=_estado_pago_id(db, "pendiente"),
        tipo="penalizacion",
        monto_total=monto,
        comision_plataforma=Decimal("0.00"),
        monto_taller=monto,
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


def asignacion_en_camino(db: Session, incidente: Incidente) -> Optional[Asignacion]:
    """
    Retorna la asignacion activa si esta en estado 'en_camino' o 'llegado'
    (o 'aceptada' como caso conservador) — usada para decidir penalizacion.
    """
    from app.models.catalogos import EstadoAsignacion

    estado_en_camino = (
        db.query(EstadoAsignacion).filter_by(nombre="en_camino").first()
    )
    estado_llegado = (
        db.query(EstadoAsignacion).filter_by(nombre="llegado").first()
    )
    estado_aceptada = (
        db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    )
    ids_objetivo = [
        e.id_estado_asignacion
        for e in (estado_en_camino, estado_llegado, estado_aceptada)
        if e
    ]
    if not ids_objetivo:
        return None

    return (
        db.query(Asignacion)
        .filter(
            Asignacion.id_incidente == incidente.id_incidente,
            Asignacion.id_estado_asignacion.in_(ids_objetivo),
        )
        .order_by(Asignacion.created_at.desc())
        .first()
    )


def _ts_transicion(db: Session, id_asignacion: int, nombre_estado: str):
    """Timestamp mas reciente en que la asignacion transiciono al estado dado.

    Lee HistorialEstadoAsignacion uniendo con EstadoAsignacion por nombre y
    tomando el created_at del registro mas reciente cuyo estado_nuevo coincide.
    """
    fila = (
        db.query(HistorialEstadoAsignacion.created_at)
        .join(
            EstadoAsignacion,
            EstadoAsignacion.id_estado_asignacion
            == HistorialEstadoAsignacion.id_estado_nuevo,
        )
        .filter(
            HistorialEstadoAsignacion.id_asignacion == id_asignacion,
            EstadoAsignacion.nombre == nombre_estado,
        )
        .order_by(HistorialEstadoAsignacion.created_at.desc())
        .first()
    )
    return fila[0] if fila else None


def evaluar_penalizacion_sla(db: Session, asignacion: Asignacion) -> Optional[Pago]:
    """Penaliza al taller si incumplio el SLA de llegada.

    Limite de llegada = eta_minutos + tolerancia, donde el porcentaje y la
    tolerancia se leen de la configuracion GLOBAL de la plataforma
    (ConfiguracionPlataforma). El tiempo real es la diferencia entre el
    timestamp del estado 'llegado' y el de 'en_camino' en
    HistorialEstadoAsignacion. Si el tiempo real supera el limite, se cobra
    pct% del monto final del servicio (asignacion.costo_estimado).

    No hace commit: usa db.add/flush. El endpoint que lo invoca commitea.
    Retorna el Pago de penalizacion creado, o None si no aplica.
    """
    if (
        asignacion.eta_minutos is None
        or asignacion.costo_estimado is None
        or Decimal(str(asignacion.costo_estimado)) <= 0
    ):
        return None

    en_camino_ts = _ts_transicion(db, asignacion.id_asignacion, "en_camino")
    llegado_ts = _ts_transicion(db, asignacion.id_asignacion, "llegado")
    if en_camino_ts is None or llegado_ts is None:
        return None

    config = get_configuracion(db)
    pct = config.sla_penalizacion_pct

    tiempo_real_min = (llegado_ts - en_camino_ts).total_seconds() / 60
    limite = asignacion.eta_minutos + config.sla_tolerancia_min
    if tiempo_real_min <= limite:
        # El taller cumplio el SLA: no hay penalizacion.
        return None

    monto = (
        Decimal(str(asignacion.costo_estimado)) * Decimal(pct) / Decimal("100")
    ).quantize(Decimal("0.01"))

    estado_pago_pendiente = (
        db.query(EstadoPago).filter(EstadoPago.nombre == "pendiente").first()
    )
    if not estado_pago_pendiente:
        estado_pago_pendiente = db.query(EstadoPago).first()
    metodo = (
        db.query(MetodoPago).order_by(MetodoPago.id_metodo_pago.asc()).first()
    )
    if not estado_pago_pendiente or not metodo:
        return None

    pago = Pago(
        id_tenant=asignacion.id_tenant,
        id_incidente=asignacion.id_incidente,
        id_metodo_pago=metodo.id_metodo_pago,
        id_estado_pago=estado_pago_pendiente.id_estado_pago,
        tipo="penalizacion",
        monto_total=monto,
        comision_plataforma=monto,
        monto_taller=Decimal("0.00"),
        referencia_externa=f"penalizacion-sla-{asignacion.id_asignacion}",
    )
    db.add(pago)
    db.flush()

    # Avisar al taller que se aplico la penalizacion.
    from app.services.notificacion_service import crear_y_enviar_notificacion

    taller = (
        db.query(Taller).filter(Taller.id_taller == asignacion.id_taller).first()
    )
    crear_y_enviar_notificacion(
        db,
        titulo="Penalizacion por retraso",
        mensaje=(
            f"Se aplico una penalizacion del {pct}% (Bs {monto}) por superar "
            "el tiempo estimado de llegada."
        ),
        id_taller=asignacion.id_taller,
        id_incidente=asignacion.id_incidente,
        push_token=taller.push_token if taller else None,
    )

    return pago
