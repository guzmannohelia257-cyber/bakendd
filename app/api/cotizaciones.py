"""Endpoints de cotizaciones."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_taller, get_current_user
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.cotizacion import Cotizacion, EstadoCotizacion
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

    token = current_tenant.set(0)
    try:
        return (
            db.query(Cotizacion)
            .filter(Cotizacion.id_incidente == id_incidente)
            .order_by(Cotizacion.created_at.desc())
            .all()
        )
    finally:
        current_tenant.reset(token)


@router.post(
    "/cotizaciones/{id_cotizacion}/aceptar",
    summary="Cliente acepta una cotizacion; crea Asignacion y rechaza las otras",
)
def aceptar(
    id_cotizacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    token = current_tenant.set(0)
    try:
        cot = db.query(Cotizacion).get(id_cotizacion)
    finally:
        current_tenant.reset(token)
    if not cot:
        raise HTTPException(404, "Cotizacion no existe")
    asig = cotizacion_service.aceptar_cotizacion(db, cot, current_user)
    return {"id_asignacion": asig.id_asignacion, "id_taller": asig.id_taller}


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
