"""
Endpoints de Notificaciones.

  POST /notificaciones/push-token          → registrar FCM token (usuario)
  POST /notificaciones/taller/push-token   → registrar FCM token (taller)
  GET  /notificaciones/mis-notificaciones  → listar notificaciones del usuario
  GET  /notificaciones/taller              → listar notificaciones del taller
  PUT  /notificaciones/{id}/leer           → marcar como leída (usuario)
  PUT  /notificaciones/taller/{id}/leer    → marcar como leída (taller)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user_model import Usuario
from app.models.taller import Taller
from app.models.transaccional import Notificacion
from app.schemas.transaccional_schema import PushTokenRequest, NotificacionResponse
from app.core.security import get_current_user, get_current_taller
from app.core.tenant_context import current_tenant

router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"],
)


# Usuarios

@router.post(
    "/push-token",
    summary="Registrar FCM token del usuario (móvil)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def registrar_push_token_usuario(
    payload: PushTokenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Un token FCM identifica al DISPOSITIVO. Si otro usuario lo tenía (uso
    # previo en este mismo teléfono), se lo quitamos para que las notificaciones
    # sigan al usuario con la sesión activa ahora. (Usuario no tiene id_tenant,
    # así que el filtro global no aplica.)
    if payload.push_token:
        db.query(Usuario).filter(
            Usuario.push_token == payload.push_token,
            Usuario.id_usuario != current_user.id_usuario,
        ).update({"push_token": None}, synchronize_session=False)
    current_user.push_token = payload.push_token
    db.commit()


@router.get(
    "/mis-notificaciones",
    response_model=List[NotificacionResponse],
    summary="Listar notificaciones del usuario autenticado",
)
def listar_notificaciones_usuario(
    solo_no_leidas: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(Notificacion).filter(Notificacion.id_usuario == current_user.id_usuario)
    if solo_no_leidas:
        q = q.filter(Notificacion.leido == False)
    return q.order_by(Notificacion.created_at.desc()).limit(50).all()


@router.put(
    "/{id_notificacion}/leer",
    summary="Marcar notificación como leída (usuario)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def marcar_leida_usuario(
    id_notificacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    notif = db.query(Notificacion).filter(
        Notificacion.id_notificacion == id_notificacion,
        Notificacion.id_usuario == current_user.id_usuario,
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    notif.leido = True
    db.commit()


# Taller

@router.post(
    "/taller/push-token",
    summary="Registrar FCM token del taller (web)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def registrar_push_token_taller(
    payload: PushTokenRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    # Mismo criterio que con usuarios: el token sigue al taller con sesión
    # activa. Taller sí tiene id_tenant, así que omitimos el filtro global para
    # poder limpiarlo en cualquier taller (otro tenant/dispositivo).
    if payload.push_token:
        tok = current_tenant.set(0)
        try:
            db.query(Taller).filter(
                Taller.push_token == payload.push_token,
                Taller.id_taller != current_taller.id_taller,
            ).update({"push_token": None}, synchronize_session=False)
        finally:
            current_tenant.reset(tok)
    current_taller.push_token = payload.push_token
    db.commit()


@router.get(
    "/taller",
    response_model=List[NotificacionResponse],
    summary="Listar notificaciones del taller autenticado",
)
def listar_notificaciones_taller(
    solo_no_leidas: bool = False,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    q = db.query(Notificacion).filter(Notificacion.id_taller == current_taller.id_taller)
    if solo_no_leidas:
        q = q.filter(Notificacion.leido == False)
    return q.order_by(Notificacion.created_at.desc()).limit(50).all()


@router.put(
    "/taller/{id_notificacion}/leer",
    summary="Marcar notificación como leída (taller)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def marcar_leida_taller(
    id_notificacion: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    notif = db.query(Notificacion).filter(
        Notificacion.id_notificacion == id_notificacion,
        Notificacion.id_taller == current_taller.id_taller,
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    notif.leido = True
    db.commit()
