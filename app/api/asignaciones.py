"""Endpoints de cancelacion de asignaciones por el cliente."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.incidente import Asignacion
from app.models.usuario import Usuario
from app.models.ubicacion import UbicacionTecnico
from app.schemas.cancelacion_schema import CancelacionResponse, CancelarAsignacionRequest
from app.schemas.tracking_schema import EtaResponse
from app.services import cancelacion_service
from app.services import tracking_service


router = APIRouter(tags=["Asignaciones"])


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
    token = current_tenant.set(0)
    try:
        asig = db.query(Asignacion).get(id_asignacion)
    finally:
        current_tenant.reset(token)
    if not asig:
        raise HTTPException(404, "Asignacion no existe")

    asig_actualizada, nuevo_estado = cancelacion_service.cancelar_asignacion(
        db=db,
        asignacion=asig,
        usuario=current_user,
        motivo=body.motivo,
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
    tok = current_tenant.set(0)
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
        ultimo.latitud, ultimo.longitud, incidente.latitud, incidente.longitud
    )
    return EtaResponse(
        distancia_km=round(dist_km, 2),
        eta_segundos=eta_seg,
        eta_minutos=round(eta_seg / 60),
    )
