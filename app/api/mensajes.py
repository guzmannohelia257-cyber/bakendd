"""
Mensajería Cliente ↔ Taller por incidente.

  GET  /mensajes/{id_incidente}          → listar mensajes (usuario o taller)
  POST /mensajes/{id_incidente}          → enviar mensaje (usuario)
  POST /mensajes/{id_incidente}/taller   → enviar mensaje (taller)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user_model import Usuario
from app.models.taller import Taller
from app.models.incidente import Incidente, Asignacion
from app.models.transaccional import Mensaje, Notificacion
from app.schemas.transaccional_schema import MensajeCreate, MensajeResponse
from app.core.security import get_current_user, get_current_taller
from app.services.notificacion_service import crear_y_enviar_notificacion

router = APIRouter(
    prefix="/mensajes",
    tags=["Mensajería"],
)


def _verificar_incidente_usuario(db: Session, id_incidente: int, id_usuario: int) -> Incidente:
    inc = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == id_usuario,
    ).first()
    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado o no te pertenece",
        )
    return inc


def _verificar_incidente_taller(db: Session, id_incidente: int, id_taller: int) -> Incidente:
    asig = db.query(Asignacion).filter(
        Asignacion.id_incidente == id_incidente,
        Asignacion.id_taller == id_taller,
    ).first()
    if not asig:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado o no asignado a tu taller",
        )
    return db.get(Incidente, id_incidente)


# Listar

@router.get(
    "/{id_incidente}",
    response_model=List[MensajeResponse],
    summary="Listar mensajes del incidente (usuario)",
)
def listar_mensajes_usuario(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _verificar_incidente_usuario(db, id_incidente, current_user.id_usuario)
    mensajes = db.query(Mensaje).filter(
        Mensaje.id_incidente == id_incidente
    ).order_by(Mensaje.created_at.asc()).all()

    # Marcar mensajes del taller como leídos para el usuario
    for m in mensajes:
        if m.id_taller is not None and not m.leido:
            m.leido = True
    db.commit()
    return mensajes


@router.get(
    "/{id_incidente}/taller",
    response_model=List[MensajeResponse],
    summary="Listar mensajes del incidente (taller)",
)
def listar_mensajes_taller(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    _verificar_incidente_taller(db, id_incidente, current_taller.id_taller)
    mensajes = db.query(Mensaje).filter(
        Mensaje.id_incidente == id_incidente
    ).order_by(Mensaje.created_at.asc()).all()

    # Marcar mensajes del usuario como leídos para el taller
    for m in mensajes:
        if m.id_usuario is not None and not m.leido:
            m.leido = True
    db.commit()
    return mensajes


# Enviar

@router.post(
    "/{id_incidente}",
    response_model=MensajeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje al taller (usuario)",
)
def enviar_mensaje_usuario(
    id_incidente: int,
    payload: MensajeCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = _verificar_incidente_usuario(db, id_incidente, current_user.id_usuario)

    msg = Mensaje(
        id_incidente=id_incidente,
        id_usuario=current_user.id_usuario,
        # Hereda el tenant del incidente (el del taller asignado). Sin esto el
        # id_tenant queda NULL y el filtro global de tenant oculta el mensaje al
        # taller (que consulta con su id_tenant en contexto).
        id_tenant=incidente.id_tenant,
        contenido=payload.contenido,
    )
    db.add(msg)
    db.flush()

    # Notificar al taller
    asig = db.query(Asignacion).filter(
        Asignacion.id_incidente == id_incidente
    ).order_by(Asignacion.created_at.desc()).first()

    if asig and asig.id_taller:
        from app.models.taller import Taller as TallerModel
        taller = db.get(TallerModel, asig.id_taller)
        crear_y_enviar_notificacion(
            db,
            titulo="Nuevo mensaje del cliente",
            mensaje=f"{current_user.nombre}: {payload.contenido[:80]}",
            id_taller=asig.id_taller,
            id_incidente=id_incidente,
            push_token=taller.push_token if taller else None,
            data={"tipo": "mensaje", "id_incidente": str(id_incidente)},
        )

    db.commit()
    db.refresh(msg)
    return msg


@router.post(
    "/{id_incidente}/taller",
    response_model=MensajeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje al cliente (taller)",
)
def enviar_mensaje_taller(
    id_incidente: int,
    payload: MensajeCreate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    incidente = _verificar_incidente_taller(db, id_incidente, current_taller.id_taller)

    msg = Mensaje(
        id_incidente=id_incidente,
        id_taller=current_taller.id_taller,
        # Hereda el tenant del incidente para que el filtro global no oculte el
        # mensaje (al cliente, sin tenant, y al propio taller que filtra por el suyo).
        id_tenant=incidente.id_tenant,
        contenido=payload.contenido,
    )
    db.add(msg)
    db.flush()

    # Notificar al cliente
    if incidente and incidente.id_usuario:
        from app.models.user_model import Usuario as UsuarioModel
        usuario = db.get(UsuarioModel, incidente.id_usuario)
        crear_y_enviar_notificacion(
            db,
            titulo=f"Mensaje de {current_taller.nombre}",
            mensaje=payload.contenido[:100],
            id_usuario=incidente.id_usuario,
            id_incidente=id_incidente,
            push_token=usuario.push_token if usuario else None,
            data={"tipo": "mensaje", "id_incidente": str(id_incidente)},
        )

    db.commit()
    db.refresh(msg)
    return msg
