"""
Router de Talleres.

El Taller es una entidad con autenticación propia (tabla `taller`).
Los técnicos ahora son USUARIOS (tabla usuario, id_rol=3).
Se registran a través de POST /usuarios/registro con email y password.

Endpoints:
  POST   /talleres/login                         → login del taller
  GET    /talleres/mi-taller                     → ver info del taller
  PUT    /talleres/mi-taller                     → editar info del taller
  
NOTA: Los endpoints de gestión de técnicos (CRUD) han sido refactorizados.
Los técnicos son usuarios con rol=3, se crean a través de /usuarios/registro.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

from app.db.session import get_db
from app.models.taller import Taller, TallerServicio
from app.models.usuario import Usuario
from app.models.incidente import Asignacion, CandidatoAsignacion, Incidente
from app.models.catalogos import EstadoAsignacion, EstadoIncidente, CategoriaProblema
from app.services.trazabilidad import (
    registrar_cambio_estado_asignacion,
    cambiar_estado_asignacion,
    cambiar_estado_incidente,
)
from app.services.notificacion_service import crear_y_enviar_notificacion
from app.schemas.taller_schema import (
    TallerLoginRequest,
    TallerUpdate,
    TallerResponse,
    TallerTokenResponse,
    MensajeResponse,
    AceptarAsignacionRequest,
    RechazarAsignacionRequest,
    AsignacionTallerResponse,
    TecnicoAsignacionResponse,
    UsuarioTallerCreate,
    UsuarioTallerUpdate,
    UsuarioTallerResponse,
    UsuarioTallerListResponse,
)
from app.schemas.incidente_schema import EvaluacionResponse
from app.models.incidente import Evaluacion
from app.core.security import (
    verify_password,
    create_access_token,
    get_current_taller,
    hash_password,
)

router = APIRouter(
    prefix="/talleres",
    tags=["Gestión de Talleres"],
    responses={
        401: {"description": "No autorizado"},
        403: {"description": "Prohibido"},
        404: {"description": "No encontrado"},
    },
)


# ============ AUTENTICACIÓN DEL TALLER ============

@router.post(
    "/login",
    response_model=TallerTokenResponse,
    summary="Login del taller",
)
def login_taller(credenciales: TallerLoginRequest, db: Session = Depends(get_db)):
    taller = db.query(Taller).filter(Taller.email == credenciales.email).first()

    if not taller or not verify_password(credenciales.password, taller.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not taller.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller ha sido desactivado",
        )

    access_token = create_access_token(subject_id=taller.id_taller, tipo="taller")
    return {"access_token": access_token, "token_type": "bearer", "taller": taller}


# ============ INFO DEL TALLER ============

@router.get("/mi-taller", response_model=TallerResponse, summary="Obtener mi taller")
def obtener_mi_taller(current_taller: Taller = Depends(get_current_taller)):
    return current_taller


@router.put("/mi-taller", response_model=TallerResponse, summary="Editar mi taller")
def editar_mi_taller(
    taller_update: TallerUpdate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    datos = taller_update.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(current_taller, campo, valor)

    db.commit()
    db.refresh(current_taller)
    return current_taller


class DisponibilidadUpdate(BaseModel):
    disponible: bool


@router.put("/mi-taller/disponibilidad", response_model=TallerResponse, summary="Toggle disponibilidad (pausa/reanuda)")
def actualizar_disponibilidad(
    payload: DisponibilidadUpdate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    current_taller.disponible = payload.disponible
    db.commit()
    db.refresh(current_taller)
    return current_taller


# ============ TÉCNICOS (Gestión de Técnicos del Taller) ============

@router.get(
    "/mi-taller/tecnicos",
    response_model=list[UsuarioTallerListResponse],
    summary="Listar técnicos del taller",
    description="Retorna los técnicos (usuarios rol=3) vinculados a este taller.",
)
def listar_tecnicos(
    activos_solo: bool = Query(True, description="¿Mostrar solo técnicos activos?"),
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    from app.models.usuario_taller import UsuarioTaller
    
    q = db.query(UsuarioTaller).filter(UsuarioTaller.id_taller == current_taller.id_taller)
    
    if activos_solo:
        q = q.filter(UsuarioTaller.activo == True)
    
    usuarios_taller = q.all()
    
    # Construir respuestas con datos del usuario
    resultados = []
    for ut in usuarios_taller:
        resultado = UsuarioTallerListResponse(
            id_usuario_taller=ut.id_usuario_taller,
            id_usuario=ut.id_usuario,
            nombre=ut.usuario.nombre,
            email=ut.usuario.email,
            telefono=ut.usuario.telefono,
            disponible=ut.disponible,
            activo=ut.activo,
            created_at=ut.created_at,
        )
        resultados.append(resultado)
    
    return resultados


def _get_tecnico_del_taller(db: Session, id_taller: int, id_usuario_taller: int):
    """Obtener un técnico vinculado a un taller específico"""
    from app.models.usuario_taller import UsuarioTaller
    
    ut = db.query(UsuarioTaller).filter(
        UsuarioTaller.id_usuario_taller == id_usuario_taller,
        UsuarioTaller.id_taller == id_taller,
    ).first()
    
    if not ut:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Técnico no encontrado en tu taller",
        )
    return ut


@router.get(
    "/mi-taller/tecnicos/{id_usuario_taller}",
    response_model=UsuarioTallerResponse,
    summary="Obtener detalles de un técnico",
)
def obtener_tecnico(
    id_usuario_taller: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    ut = _get_tecnico_del_taller(db, current_taller.id_taller, id_usuario_taller)
    
    return UsuarioTallerResponse(
        id_usuario_taller=ut.id_usuario_taller,
        id_usuario=ut.id_usuario,
        id_taller=ut.id_taller,
        disponible=ut.disponible,
        activo=ut.activo,
        latitud=ut.latitud,
        longitud=ut.longitud,
        created_at=ut.created_at,
        nombre=ut.usuario.nombre,
        email=ut.usuario.email,
        telefono=ut.usuario.telefono,
    )


@router.post(
    "/mi-taller/tecnicos",
    response_model=UsuarioTallerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar técnico al taller",
    description="Crea un usuario técnico (rol=3) y lo vincula a este taller.",
)
def crear_tecnico(
    tecnico_data: UsuarioTallerCreate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    from app.models.usuario_taller import UsuarioTaller
    
    # 1. Validar que el email no existe
    usuario_existe = db.query(Usuario).filter(Usuario.email == tecnico_data.email).first()
    if usuario_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    
    # 2. Crear usuario técnico (rol=3)
    nuevo_usuario = Usuario(
        id_rol=3,  # Rol técnico
        nombre=tecnico_data.nombre,
        email=tecnico_data.email,
        telefono=tecnico_data.telefono,
        password_hash=hash_password(tecnico_data.password),
        activo=True,
    )
    db.add(nuevo_usuario)
    db.flush()  # Obtener el ID sin hacer commit
    
    # 3. Vincular usuario a taller con UsuarioTaller
    usuario_taller = UsuarioTaller(
        id_usuario=nuevo_usuario.id_usuario,
        id_taller=current_taller.id_taller,
        disponible=True,
        activo=True,
    )
    db.add(usuario_taller)
    db.commit()
    db.refresh(usuario_taller)
    
    return UsuarioTallerResponse(
        id_usuario_taller=usuario_taller.id_usuario_taller,
        id_usuario=usuario_taller.id_usuario,
        id_taller=usuario_taller.id_taller,
        disponible=usuario_taller.disponible,
        activo=usuario_taller.activo,
        latitud=usuario_taller.latitud,
        longitud=usuario_taller.longitud,
        created_at=usuario_taller.created_at,
        nombre=nuevo_usuario.nombre,
        email=nuevo_usuario.email,
        telefono=nuevo_usuario.telefono,
    )


@router.put(
    "/mi-taller/tecnicos/{id_usuario_taller}",
    response_model=UsuarioTallerResponse,
    summary="Actualizar datos de un técnico",
    description="Actualiza disponibilidad, ubicación y otros datos del técnico.",
)
def editar_tecnico(
    id_usuario_taller: int,
    tecnico_update: UsuarioTallerUpdate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    ut = _get_tecnico_del_taller(db, current_taller.id_taller, id_usuario_taller)
    
    datos = tecnico_update.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        if valor is not None:
            setattr(ut, campo, valor)
    
    db.commit()
    db.refresh(ut)
    
    return UsuarioTallerResponse(
        id_usuario_taller=ut.id_usuario_taller,
        id_usuario=ut.id_usuario,
        id_taller=ut.id_taller,
        disponible=ut.disponible,
        activo=ut.activo,
        latitud=ut.latitud,
        longitud=ut.longitud,
        created_at=ut.created_at,
        nombre=ut.usuario.nombre,
        email=ut.usuario.email,
        telefono=ut.usuario.telefono,
    )


@router.delete(
    "/mi-taller/tecnicos/{id_usuario_taller}",
    response_model=MensajeResponse,
    summary="Remover técnico del taller (baja lógica)",
)
def remover_tecnico(
    id_usuario_taller: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    ut = _get_tecnico_del_taller(db, current_taller.id_taller, id_usuario_taller)
    ut.activo = False
    db.commit()
    return MensajeResponse(mensaje="Técnico removido del taller correctamente")


# ============ ASIGNACIONES (el taller responde al cliente) ============

def _get_asignacion_del_taller(db: Session, id_taller: int, id_asignacion: int) -> Asignacion:
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_taller == id_taller,
    ).first()
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no pertenece a tu taller",
        )
    return asignacion


@router.get(
    "/mi-taller/asignaciones",
    response_model=List[AsignacionTallerResponse],
    summary="Listar asignaciones del taller",
    description="Retorna las asignaciones dirigidas a este taller. Filtra por estado y fechas",
)
def listar_asignaciones(
    estado: Optional[str] = Query(None, description="Filtrar por nombre de estado: pendiente|aceptada|rechazada|en_camino|completada"),
    desde: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    q = db.query(Asignacion).filter(Asignacion.id_taller == current_taller.id_taller)

    # Evitar solicitudes de incidentes cancelados en cualquier estado
    q = q.join(Incidente).join(EstadoIncidente).filter(EstadoIncidente.nombre != "cancelado")
    
    # Filtrar por estado
    if estado:
        q = q.join(EstadoAsignacion).filter(EstadoAsignacion.nombre == estado)
    
    # Filtrar por rango de fechas
    if desde:
        from datetime import datetime
        q = q.filter(Asignacion.created_at >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        from datetime import datetime
        q = q.filter(Asignacion.created_at <= datetime.combine(hasta, datetime.max.time()))
    
    return q.order_by(Asignacion.created_at.desc()).all()


@router.get(
    "/mi-taller/asignaciones/{id_asignacion}",
    response_model=AsignacionTallerResponse,
    summary="Detalle de una asignación",
)
def obtener_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    return _get_asignacion_del_taller(db, current_taller.id_taller, id_asignacion)


@router.put(
    "/mi-taller/asignaciones/{id_asignacion}/aceptar",
    response_model=AsignacionTallerResponse,
    summary="Aceptar una asignación",
    description="El taller confirma que se hará cargo del incidente. Pasa a estado 'aceptada'.",
)
def aceptar_asignacion(
    id_asignacion: int,
    payload: AceptarAsignacionRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    asignacion = _get_asignacion_del_taller(db, current_taller.id_taller, id_asignacion)

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if estado_actual and estado_actual.nombre not in ("pendiente",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La asignación ya está en estado '{estado_actual.nombre}', no se puede aceptar",
        )

    if payload.id_usuario is not None:
        # Validar que el usuario existe y es técnico (rol=3)
        tecnico_user = db.query(Usuario).filter(
            Usuario.id_usuario == payload.id_usuario,
            Usuario.id_rol == 3,
            Usuario.activo == True
        ).first()
        if not tecnico_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario técnico no encontrado o no está activo",
            )

        # Validar que ese técnico pertenezca a este taller
        from app.models.usuario_taller import UsuarioTaller
        relacion_tecnico = db.query(UsuarioTaller).filter(
            UsuarioTaller.id_usuario == payload.id_usuario,
            UsuarioTaller.id_taller == current_taller.id_taller,
            UsuarioTaller.activo == True,
        ).first()
        if not relacion_tecnico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El técnico no pertenece a tu taller o está inactivo",
            )
        
        # 🔴 VALIDACIÓN CRÍTICA: Un técnico NO puede tener más de una asignación activa a la vez
        asignacion_activa_existente = db.query(Asignacion).filter(
            Asignacion.id_usuario == payload.id_usuario,
            Asignacion.id_estado_asignacion.in_(
                db.query(EstadoAsignacion.id_estado_asignacion).filter(
                    EstadoAsignacion.nombre.in_(["aceptada", "en_camino"])
                )
            ),
            Asignacion.id_asignacion != id_asignacion  # Excluir la asignación actual
        ).first()
        
        if asignacion_activa_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El técnico ya tiene una asignación activa (ID: {asignacion_activa_existente.id_asignacion}). Un técnico solo puede tener una asignación a la vez.",
            )
        
        asignacion.id_usuario = payload.id_usuario

    if payload.eta_minutos is not None:
        asignacion.eta_minutos = payload.eta_minutos
    if payload.nota:
        asignacion.nota_taller = payload.nota

    # A.1: usar trazabilidad para registrar el cambio de estado
    observacion = f"Aceptada por taller {current_taller.id_taller}"
    if payload.eta_minutos is not None:
        observacion += f". ETA: {payload.eta_minutos} min"
    if payload.id_usuario is not None:
        observacion += f". Técnico asignado: {payload.id_usuario}"

    try:
        cambiar_estado_asignacion(db, asignacion, "aceptada", observacion=observacion)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Notificaciones: cliente y técnico asignado
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente and incidente.id_usuario:
        cliente = db.get(Usuario, incidente.id_usuario)
        if cliente:
            mensaje_cliente = f"Tu solicitud fue aceptada por {current_taller.nombre}."
            if payload.id_usuario is not None:
                mensaje_cliente += f" Técnico asignado: {tecnico_user.nombre}."
            if payload.eta_minutos is not None:
                mensaje_cliente += f" ETA: {payload.eta_minutos} min."

            crear_y_enviar_notificacion(
                db,
                titulo="Solicitud aceptada",
                mensaje=mensaje_cliente,
                id_usuario=cliente.id_usuario,
                id_incidente=incidente.id_incidente,
                push_token=cliente.push_token,
                data={
                    "tipo": "asignacion_aceptada",
                    "id_incidente": str(incidente.id_incidente),
                    "id_asignacion": str(asignacion.id_asignacion),
                },
            )

    if payload.id_usuario is not None:
        mensaje_tecnico = f"Nueva asignación en {current_taller.nombre}."
        if payload.eta_minutos is not None:
            mensaje_tecnico += f" ETA: {payload.eta_minutos} min."

        crear_y_enviar_notificacion(
            db,
            titulo="Nueva asignación",
            mensaje=mensaje_tecnico,
            id_usuario=tecnico_user.id_usuario,
            id_incidente=asignacion.id_incidente,
            push_token=tecnico_user.push_token,
            data={
                "tipo": "asignacion_tecnico",
                "id_incidente": str(asignacion.id_incidente),
                "id_asignacion": str(asignacion.id_asignacion),
            },
        )

    db.commit()
    db.refresh(asignacion)
    return asignacion


@router.put(
    "/mi-taller/asignaciones/{id_asignacion}/rechazar",
    response_model=AsignacionTallerResponse,
    summary="Rechazar una asignación",
    description="El taller declina el incidente. Se marca como 'rechazada' y el cliente puede elegir otro taller.",
)
def rechazar_asignacion(
    id_asignacion: int,
    payload: RechazarAsignacionRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    asignacion = _get_asignacion_del_taller(db, current_taller.id_taller, id_asignacion)

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if estado_actual and estado_actual.nombre not in ("pendiente",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La asignación ya está en estado '{estado_actual.nombre}', no se puede rechazar",
        )

    estado_rechazada = db.query(EstadoAsignacion).filter_by(nombre="rechazada").first()
    if not estado_rechazada:
        raise HTTPException(status_code=500, detail="Catálogo estado 'rechazada' no existe")

    id_estado_anterior = asignacion.id_estado_asignacion
    asignacion.id_estado_asignacion = estado_rechazada.id_estado_asignacion
    asignacion.nota_taller = payload.motivo
    
    # Registrar cambio de estado en historial
    registrar_cambio_estado_asignacion(
        db, asignacion, id_estado_anterior, estado_rechazada.id_estado_asignacion,
        observacion=f"Rechazada por taller {current_taller.id_taller}. Motivo: {payload.motivo}"
    )

    # Desmarcar al taller como candidato seleccionado para que el cliente pueda elegir otro
    db.query(CandidatoAsignacion).filter(
        CandidatoAsignacion.id_incidente == asignacion.id_incidente,
        CandidatoAsignacion.id_taller == current_taller.id_taller,
    ).update({CandidatoAsignacion.seleccionado: False}, synchronize_session=False)

    # B.1: Reasignación automática — buscar siguiente candidato
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        # Obtener lista de talleres que ya rechazaron este incidente
        rechazos_previos = db.query(Asignacion.id_taller).join(EstadoAsignacion).filter(
            Asignacion.id_incidente == incidente.id_incidente,
            EstadoAsignacion.nombre == "rechazada",
        ).all()
        ids_rechazantes = {r[0] for r in rechazos_previos}
        
        # Buscar el siguiente candidato con mejor score (excluyendo rechazantes)
        siguiente = db.query(CandidatoAsignacion).filter(
            CandidatoAsignacion.id_incidente == incidente.id_incidente,
            ~CandidatoAsignacion.id_taller.in_(ids_rechazantes or [-1]),
        ).order_by(CandidatoAsignacion.score_total.desc()).first()
        
        if siguiente:
            # Marcar nuevo candidato como seleccionado
            siguiente.seleccionado = True
            
            # Crear nueva asignación para el siguiente candidato
            estado_pendiente = db.query(EstadoAsignacion).filter_by(nombre="pendiente").first()
            if estado_pendiente:
                nueva_asignacion = Asignacion(
                    id_incidente=incidente.id_incidente,
                    id_taller=siguiente.id_taller,
                    id_estado_asignacion=estado_pendiente.id_estado_asignacion,
                )
                db.add(nueva_asignacion)
                db.flush()
                
                # Registrar creación de nueva asignación en historial
                registrar_cambio_estado_asignacion(
                    db, nueva_asignacion, None, estado_pendiente.id_estado_asignacion,
                    observacion=f"Reasignación automática tras rechazo de taller {current_taller.id_taller}. "
                                f"Nuevo taller: {siguiente.id_taller} (score: {siguiente.score_total:.2f})"
                )
                # TODO CU-32: enviar push notification al nuevo taller
        else:
            # No hay más candidatos — dejar para reasignación manual o cancelar
            import logging
            logger = logging.getLogger("talleres")
            logger.warning(
                f"[B.1] Incidente {incidente.id_incidente}: no hay más candidatos tras rechazo de {current_taller.id_taller}"
            )

    db.commit()
    db.refresh(asignacion)
    return asignacion


# ============ A.3 — CU-10: EVALUACIONES DEL TALLER ============

@router.get(
    "/mi-taller/evaluaciones",
    response_model=List[EvaluacionResponse],
    summary="Reseñas recibidas por el taller",
    description="Lista las evaluaciones (estrellas + comentario) que los clientes dejaron al taller.",
)
def mis_evaluaciones(
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    return (
        db.query(Evaluacion)
        .filter(Evaluacion.id_taller == current_taller.id_taller)
        .order_by(Evaluacion.created_at.desc())
        .all()
    )


# ============ HISTORIAL DE ATENCIONES ============

@router.get(
    "/mi-taller/historial",
    response_model=List[AsignacionTallerResponse],
    summary="Historial de atenciones completadas del taller",
    description="Retorna todas las asignaciones con estado 'completada' del taller, con paginación.",
)
def historial_atenciones(
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página"),
    desde: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    q = (
        db.query(Asignacion)
        .join(EstadoAsignacion)
        .filter(
            Asignacion.id_taller == current_taller.id_taller,
            EstadoAsignacion.nombre == "completada",
        )
    )

    if desde:
        from datetime import datetime as dt
        q = q.filter(Asignacion.created_at >= dt.combine(desde, dt.min.time()))
    if hasta:
        from datetime import datetime as dt
        q = q.filter(Asignacion.created_at <= dt.combine(hasta, dt.max.time()))

    total = q.count()
    items = q.order_by(Asignacion.created_at.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return items


# ============ GESTIÓN DE SERVICIOS DEL TALLER ============

class CategoriaResponse(BaseModel):
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


class ServicioTallerResponse(BaseModel):
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None
    servicio_movil: bool

    class Config:
        from_attributes = True


class ActualizarServiciosRequest(BaseModel):
    categorias: List[int]


@router.get(
    "/categorias",
    response_model=List[CategoriaResponse],
    summary="Listar todas las categorías disponibles",
    description="Retorna el catálogo completo de categorías para que el taller elija cuáles ofrece.",
)
def listar_categorias_disponibles(
    db: Session = Depends(get_db),
    _taller: Taller = Depends(get_current_taller),
):
    return db.query(CategoriaProblema).order_by(CategoriaProblema.id_categoria).all()


@router.get(
    "/mi-taller/servicios",
    response_model=List[ServicioTallerResponse],
    summary="Listar servicios actuales del taller",
)
def mis_servicios(
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    rows = (
        db.query(TallerServicio, CategoriaProblema)
        .join(CategoriaProblema, CategoriaProblema.id_categoria == TallerServicio.id_categoria)
        .filter(TallerServicio.id_taller == current_taller.id_taller)
        .order_by(CategoriaProblema.id_categoria)
        .all()
    )
    return [
        ServicioTallerResponse(
            id_categoria=cat.id_categoria,
            nombre=cat.nombre,
            descripcion=cat.descripcion,
            servicio_movil=srv.servicio_movil,
        )
        for srv, cat in rows
    ]


@router.put(
    "/mi-taller/servicios",
    response_model=List[ServicioTallerResponse],
    summary="Actualizar servicios del taller",
    description="Reemplaza la lista completa de servicios. Enviar lista vacía elimina todos.",
)
def actualizar_mis_servicios(
    payload: ActualizarServiciosRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    # Borrar servicios actuales
    db.query(TallerServicio).filter(
        TallerServicio.id_taller == current_taller.id_taller
    ).delete(synchronize_session=False)

    # Insertar nuevos (solo IDs válidos)
    nuevos = []
    for id_cat in payload.categorias:
        cat = db.get(CategoriaProblema, id_cat)
        if cat:
            srv = TallerServicio(
                id_taller=current_taller.id_taller,
                id_categoria=id_cat,
                servicio_movil=True,
            )
            db.add(srv)
            nuevos.append(ServicioTallerResponse(
                id_categoria=cat.id_categoria,
                nombre=cat.nombre,
                descripcion=cat.descripcion,
                servicio_movil=True,
            ))

    db.commit()
    return nuevos
