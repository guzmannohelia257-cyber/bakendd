"""
Pagos Stripe.

Endpoints:
  POST /pagos/crear-intent   -> crea PaymentIntent en Stripe
  POST /pagos/confirmar      -> webhook de Stripe para actualizar estado
  GET  /pagos/{id_incidente} -> consultar estado del pago
"""
import json
from typing import Optional, List

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.models.user_model import Usuario
from app.models.incidente import Incidente, Asignacion
from app.models.catalogos import EstadoPago, MetodoPago, EstadoAsignacion
from app.models.transaccional import Pago
from app.schemas.transaccional_schema import (
    PagoIntentRequest,
    PagoResponse,
    StripeIntentResponse,
    PagoClienteItem,
    ConfirmarPagoAppRequest,
)
from app.core.security import get_current_user
from app.services import pago_service

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos (Stripe)"],
)

settings = get_settings()


def _get_estado_pago_id(db: Session, nombre_estado: str) -> int:
    estado = db.query(EstadoPago).filter(EstadoPago.nombre == nombre_estado).first()
    if not estado:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No existe estado_pago '{nombre_estado}' en catálogo",
        )
    return estado.id_estado_pago


def _get_default_metodo_pago_id(db: Session) -> int:
    metodo = db.query(MetodoPago).order_by(MetodoPago.id_metodo_pago.asc()).first()
    if not metodo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existen métodos de pago en catálogo",
        )
    return metodo.id_metodo_pago


def _require_stripe_secret_key() -> str:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falta STRIPE_SECRET_KEY en variables de entorno",
        )
    return settings.STRIPE_SECRET_KEY


def _load_stripe_api_key() -> None:
    stripe.api_key = _require_stripe_secret_key()


def _aplicar_comision(db: Session, pago: Pago) -> None:
    """Aplica la comision configurable de la plataforma y recalcula el monto del
    taller. El % se lee de la configuracion global (admin); antes era 10% fijo."""
    from app.services.pago_service import get_configuracion

    monto = float(pago.monto_total or 0)
    pct = float(get_configuracion(db).comision_plataforma_pct or 0)
    comision = round(monto * pct / 100, 2)
    pago.comision_plataforma = comision
    pago.monto_taller = round(monto - comision, 2)


def _actualizar_pago_desde_intent(
    db: Session,
    payment_intent: dict,
    estado_nombre: str,
) -> None:
    referencia = payment_intent.get("id")
    metadata = payment_intent.get("metadata") or {}
    id_incidente_raw = metadata.get("id_incidente")
    id_metodo_raw = metadata.get("id_metodo_pago")

    pago: Optional[Pago] = None
    if referencia:
        pago = db.query(Pago).filter(Pago.referencia_externa == referencia).first()

    if not pago and id_incidente_raw:
        try:
            id_incidente_int = int(id_incidente_raw)
        except (TypeError, ValueError):
            id_incidente_int = None
        if id_incidente_int:
            pago = db.query(Pago).filter(Pago.id_incidente == id_incidente_int).first()

    if not pago:
        if not id_incidente_raw:
            return
        try:
            id_incidente_int = int(id_incidente_raw)
        except (TypeError, ValueError):
            return

        try:
            id_metodo_int = int(id_metodo_raw) if id_metodo_raw is not None else _get_default_metodo_pago_id(db)
        except (TypeError, ValueError):
            id_metodo_int = _get_default_metodo_pago_id(db)

        metodo = db.query(MetodoPago).filter(MetodoPago.id_metodo_pago == id_metodo_int).first()
        if not metodo:
            id_metodo_int = _get_default_metodo_pago_id(db)

        monto_total = (payment_intent.get("amount") or 0) / 100.0
        pago = Pago(
            id_incidente=id_incidente_int,
            id_metodo_pago=id_metodo_int,
            id_estado_pago=_get_estado_pago_id(db, estado_nombre),
            monto_total=monto_total,
            comision_plataforma=0,
            monto_taller=monto_total,
            referencia_externa=referencia,
        )
        if estado_nombre == "completado":
            _aplicar_comision(db, pago)
        db.add(pago)
        return

    pago.id_estado_pago = _get_estado_pago_id(db, estado_nombre)
    if referencia:
        pago.referencia_externa = referencia
    if estado_nombre == "completado":
        _aplicar_comision(db, pago)


@router.post(
    "/crear-intent",
    response_model=StripeIntentResponse,
    summary="Crear PaymentIntent de Stripe",
    description="Crea el PaymentIntent y deja un registro pendiente en la tabla pago.",
)
def crear_payment_intent(
    payload: PagoIntentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden crear pagos",
        )

    incidente = db.get(Incidente, payload.id_incidente)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado",
        )

    if incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes pagar un incidente que no te pertenece",
        )

    metodo = db.query(MetodoPago).filter(MetodoPago.id_metodo_pago == payload.id_metodo_pago).first()
    if not metodo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Método de pago no encontrado",
        )

    _load_stripe_api_key()

    monto_centavos = int(round(payload.monto_total * 100))
    try:
        intent = stripe.PaymentIntent.create(
            amount=monto_centavos,
            currency="usd",
            automatic_payment_methods={"enabled": True},
            metadata={
                "id_incidente": str(payload.id_incidente),
                "id_usuario": str(current_user.id_usuario),
                "id_metodo_pago": str(payload.id_metodo_pago),
            },
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error creando PaymentIntent en Stripe: {getattr(exc, 'user_message', str(exc))}",
        )

    estado_pendiente = _get_estado_pago_id(db, "pendiente")
    # Filtrar por tipo='servicio' evita sobrescribir un Pago tipo='preauth' o
    # 'penalizacion' que pudo crearse para el mismo incidente.
    pago = (
        db.query(Pago)
        .filter(
            Pago.id_incidente == payload.id_incidente,
            Pago.tipo == "servicio",
        )
        .first()
    )

    if pago:
        pago.id_metodo_pago = payload.id_metodo_pago
        pago.id_estado_pago = estado_pendiente
        pago.monto_total = payload.monto_total
        pago.comision_plataforma = 0
        pago.monto_taller = payload.monto_total
        pago.referencia_externa = intent.id
    else:
        pago = Pago(
            id_incidente=payload.id_incidente,
            id_metodo_pago=payload.id_metodo_pago,
            id_estado_pago=estado_pendiente,
            tipo="servicio",
            monto_total=payload.monto_total,
            comision_plataforma=0,
            monto_taller=payload.monto_total,
            referencia_externa=intent.id,
        )
        db.add(pago)

    # La comision de la plataforma se aplica desde la creacion del pago para que
    # el monto del taller sea correcto aunque el webhook/confirmacion no llegue
    # (se vuelve a aplicar, idempotente, al confirmarse el pago). Se protege para
    # no bloquear la creacion del pago si la configuracion no estuviera disponible.
    try:
        _aplicar_comision(db, pago)
    except Exception:
        pass

    db.commit()

    return StripeIntentResponse(
        client_secret=intent.client_secret,
        payment_intent_id=intent.id,
        monto_centavos=intent.amount,
    )


@router.post(
    "/confirmar",
    summary="Webhook Stripe: confirmar/actualizar pago",
)
async def confirmar_pago(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    _load_stripe_api_key()

    payload_bytes = await request.body()

    if settings.STRIPE_WEBHOOK_SECRET:
        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falta header Stripe-Signature",
            )
        try:
            event = stripe.Webhook.construct_event(
                payload=payload_bytes,
                sig_header=stripe_signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload inválido",
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Firma Stripe inválida",
            )
    else:
        try:
            event = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload JSON inválido",
            )

    event_type = event.get("type")
    payment_intent = (event.get("data") or {}).get("object")

    if event_type == "payment_intent.succeeded":
        _actualizar_pago_desde_intent(db, payment_intent or {}, "completado")
    elif event_type == "payment_intent.processing":
        _actualizar_pago_desde_intent(db, payment_intent or {}, "procesando")
    elif event_type in {"payment_intent.payment_failed", "payment_intent.canceled"}:
        _actualizar_pago_desde_intent(db, payment_intent or {}, "fallido")

    db.commit()
    return {"ok": True, "event_type": event_type}


@router.post(
    "/confirmar-app",
    summary="Confirmar pago desde la app móvil",
    description="Verifica el estado del PaymentIntent con Stripe y actualiza el pago en BD.",
)
def confirmar_pago_app(
    payload: ConfirmarPagoAppRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _load_stripe_api_key()

    try:
        intent = stripe.PaymentIntent.retrieve(payload.payment_intent_id)
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error consultando Stripe: {getattr(exc, 'user_message', str(exc))}",
        )

    estado_map = {
        "succeeded": "completado",
        "processing": "procesando",
        "requires_payment_method": "fallido",
        "canceled": "fallido",
    }
    estado_nombre = estado_map.get(intent.status, "pendiente")

    pago = db.query(Pago).filter(Pago.referencia_externa == payload.payment_intent_id).first()
    if pago:
        incidente = db.get(Incidente, pago.id_incidente)
        if incidente and incidente.id_usuario != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes confirmar un pago que no te pertenece",
            )
        pago.id_estado_pago = _get_estado_pago_id(db, estado_nombre)
        if estado_nombre == "completado":
            _aplicar_comision(db, pago)
        db.commit()

    return {"estado": estado_nombre, "payment_intent_status": intent.status}


@router.get(
    "/mis-pagos",
    response_model=List[PagoClienteItem],
    summary="Listar pagos del cliente",
    description="Retorna pagos registrados y servicios completados pendientes de pago del cliente autenticado.",
)
def listar_mis_pagos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden consultar sus pagos",
        )

    sub_asig_completada = (
        db.query(
            Asignacion.id_incidente.label("id_incidente"),
            func.max(Asignacion.id_asignacion).label("id_asignacion"),
        )
        .join(
            EstadoAsignacion,
            EstadoAsignacion.id_estado_asignacion == Asignacion.id_estado_asignacion,
        )
        .filter(EstadoAsignacion.nombre == "completada")
        .group_by(Asignacion.id_incidente)
        .subquery()
    )

    rows = (
        db.query(Incidente, Asignacion, Pago, EstadoPago)
        .outerjoin(sub_asig_completada, sub_asig_completada.c.id_incidente == Incidente.id_incidente)
        .outerjoin(Asignacion, Asignacion.id_asignacion == sub_asig_completada.c.id_asignacion)
        # Filtrar tipo='servicio': sin este filtro, un mismo incidente que tenga
        # también un Pago tipo='preauth' o 'penalizacion' aparece duplicado.
        .outerjoin(
            Pago,
            and_(Pago.id_incidente == Incidente.id_incidente, Pago.tipo == "servicio"),
        )
        .outerjoin(EstadoPago, EstadoPago.id_estado_pago == Pago.id_estado_pago)
        .filter(Incidente.id_usuario == current_user.id_usuario)
        .filter(or_(Pago.id_pago.isnot(None), sub_asig_completada.c.id_asignacion.isnot(None)))
        .order_by(Incidente.created_at.desc())
        .all()
    )

    resultado: List[PagoClienteItem] = []
    for incidente, asignacion, pago, estado_pago in rows:
        monto = (
            float(pago.monto_total)
            if pago and pago.monto_total is not None
            else float(asignacion.costo_estimado or 0)
        )
        estado = estado_pago.nombre if estado_pago else "pendiente"

        resultado.append(
            PagoClienteItem(
                id_incidente=incidente.id_incidente,
                id_pago=pago.id_pago if pago else None,
                monto_total=monto,
                estado=estado,
                referencia_externa=pago.referencia_externa if pago else None,
                created_at=pago.created_at if pago else incidente.created_at,
                updated_at=pago.updated_at if pago else incidente.updated_at,
            )
        )

    return resultado


@router.post(
    "/preautorizar/{id_incidente}",
    summary="Pre-autorizar pago: reserva el monto estimado (capture_method=manual)",
    description=(
        "Estima un costo referencial a partir de la categoria IA + tarifa promedio "
        "de talleres. Crea un PaymentIntent en modo manual_capture: NO cobra "
        "todavia, solo reserva el monto en la tarjeta del cliente. Si el cliente "
        "no tiene fondos, no se buscara taller."
    ),
)
def preautorizar_endpoint(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 1:
        raise HTTPException(403, "Solo clientes pueden pre-autorizar pagos")

    incidente = db.get(Incidente, id_incidente)
    if not incidente:
        raise HTTPException(404, "Incidente no encontrado")
    if incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(403, "Este incidente no te pertenece")

    monto = pago_service.estimar_costo(db, incidente)
    return pago_service.preautorizar(db, incidente, monto)


class CapturarRequest(BaseModel):
    monto_final: Optional[float] = None


@router.post(
    "/capturar/{id_incidente}",
    summary="Capturar pago al finalizar el servicio (cobro real)",
    description=(
        "Toma el PaymentIntent pre-autorizado y lo captura con el monto final. "
        "Si monto_final es null, captura el monto pre-autorizado completo."
    ),
)
def capturar_endpoint(
    id_incidente: int,
    body: CapturarRequest | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol not in (1, 3, 4):  # cliente, técnico o admin
        raise HTTPException(403, "Rol sin permiso para capturar pagos")

    incidente = db.get(Incidente, id_incidente)
    if not incidente:
        raise HTTPException(404, "Incidente no encontrado")

    if current_user.id_rol == 1 and incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(403, "Este incidente no te pertenece")

    from decimal import Decimal as _Dec

    monto_final = None
    if body and body.monto_final is not None:
        monto_final = _Dec(str(body.monto_final))

    pago = pago_service.capturar(db, incidente, monto_final=monto_final)
    return {
        "id_pago": pago.id_pago,
        "tipo": pago.tipo,
        "monto_total": float(pago.monto_total),
        "comision_plataforma": float(pago.comision_plataforma),
        "monto_taller": float(pago.monto_taller),
        "referencia_externa": pago.referencia_externa,
    }


@router.get(
    "/{id_incidente}",
    response_model=PagoResponse,
    summary="Consultar pago de un incidente",
)
def obtener_pago(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.get(Incidente, id_incidente)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado",
        )

    if incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes consultar pagos de un incidente que no te pertenece",
        )

    pago = (
        db.query(Pago)
        .filter(Pago.id_incidente == id_incidente, Pago.tipo == "servicio")
        .first()
    )
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe pago registrado para este incidente",
        )

    estado_obj = pago.estado
    return PagoResponse(
        id_pago=pago.id_pago,
        id_incidente=pago.id_incidente,
        monto_total=float(pago.monto_total),
        comision_plataforma=float(pago.comision_plataforma),
        monto_taller=float(pago.monto_taller),
        referencia_externa=pago.referencia_externa,
        estado=estado_obj.nombre if estado_obj else "desconocido",
        created_at=pago.created_at,
    )
