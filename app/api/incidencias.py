"""
Router de Incidencias (CU-06)
Endpoints para:
- Obtener categorías de problemas (GET /incidencias/categorias)
- Obtener niveles de prioridad (GET /incidencias/prioridades)
- Reportar una emergencia (POST /incidencias)
- Listar incidencias del usuario (GET /incidencias/mis-incidencias)
- Obtener detalles de una incidencia (GET /incidencias/{id_incidente})
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.db.session import get_db
from app.models.usuario import Usuario, Vehiculo
from app.models.usuario_taller import UsuarioTaller
from app.models.incidente import Incidente, Asignacion, CandidatoAsignacion, Evaluacion
from app.models.catalogos import CategoriaProblema, Prioridad, EstadoIncidente, EstadoAsignacion
from app.models.transaccional import Metrica
from pydantic import BaseModel, Field
from app.schemas.incidente_schema import (
    IncidenteCreate,
    IncidenteResponse,
    IncidenteDetalle,
    CandidatoAsignacionResponse,
    TallerMini,
    CategoriaResponse,
    PrioridadResponse,
    EstadoIncidenteResponse,
    EvaluacionCreate,
    EvaluacionResponse,
)
from app.core.security import get_current_user
from app.services.ia_service import clasificar_incidente

router = APIRouter(
    prefix="/incidencias",
    tags=["Gestión de Incidencias (CU-06)"],
    responses={
        400: {"description": "Bad Request - Validación fallida"},
        401: {"description": "Unauthorized - Token inválido o expirado"},
        404: {"description": "Not Found - Recurso no encontrado"},
    }
)


# ==========================================
# CATÁLOGOS (Lectura)
# ==========================================

@router.get(
    "/categorias",
    response_model=List[CategoriaResponse],
    summary="Obtener categorías de problemas",
    description="Retorna todas las categorías disponibles para reportar un problema"
)
def obtener_categorias(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que Flutter obtenga las categorías disponibles.
    Ejemplo: Falla Mecánica, Falla Eléctrica, Accidente, Descompostura, etc.
    """
    categorias = db.query(CategoriaProblema).all()
    
    if not categorias:
        raise HTTPException(
            status_code=404,
            detail="No hay categorías disponibles"
        )
    
    return categorias


@router.get(
    "/prioridades",
    response_model=List[PrioridadResponse],
    summary="Obtener niveles de prioridad",
    description="Retorna todos los niveles de prioridad disponibles"
)
def obtener_prioridades(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que Flutter obtenga los niveles de prioridad.
    Ejemplo: baja (2 horas), media (1 hora), alta (30 min), crítica (15 min)
    """
    prioridades = db.query(Prioridad).all()
    
    if not prioridades:
        raise HTTPException(
            status_code=404,
            detail="No hay prioridades disponibles"
        )
    
    return prioridades


@router.get(
    "/estados",
    response_model=List[EstadoIncidenteResponse],
    summary="Obtener estados de incidente",
    description="Retorna todos los estados posibles de un incidente"
)
def obtener_estados(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que Flutter obtenga los estados.
    Estados: pendiente, en_proceso, atendido, cancelado
    """
    estados = db.query(EstadoIncidente).all()
    
    if not estados:
        raise HTTPException(
            status_code=404,
            detail="No hay estados disponibles"
        )
    
    return estados


# ==========================================
# OPERACIONES (Crear, Listar, Obtener)
# ==========================================

@router.post(
    "/",
    response_model=IncidenteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reportar una emergencia vehicular",
    description="Crea un nuevo incidente. Valida que el vehículo pertenezca al usuario."
)
def reportar_incidencia(
    incidente_in: IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    🚨 ENDPOINT CRÍTICO DEL SISTEMA 🚨
    
    Cuando el usuario presiona "¡Auxilio!", se ejecuta esto.
    
    Validaciones:
    1. El vehículo existe
    2. El vehículo pertenece al usuario autenticado
    3. El vehículo está activo (no está eliminado)
    
    Seguridad:
    - El id_usuario se asigna automáticamente desde el JWT (no se puede falsificar)
    - El estado inicial siempre es "pendiente" (id=1)
    - id_categoria e id_prioridad se rellenan después por IA (inician NULL)
    
    Retorna: Incidente creado con id_incidente
    """
    
    # ✅ VALIDACIÓN 0: Solo 1 incidente activo por usuario
    incidente_activo = db.query(Incidente).join(
        EstadoIncidente, Incidente.id_estado == EstadoIncidente.id_estado
    ).filter(
        Incidente.id_usuario == current_user.id_usuario,
        EstadoIncidente.nombre.in_(["pendiente", "en_proceso"])
    ).first()
    if incidente_activo:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Ya tienes un incidente activo (#{incidente_activo.id_incidente}). "
                "Espera a que sea atendido o cancélalo antes de reportar otro."
            ),
        )

    # ✅ VALIDACIÓN 1: Verificar que el vehículo existe Y pertenece a este usuario
    vehiculo = db.query(Vehiculo).filter(
        Vehiculo.id_vehiculo == incidente_in.id_vehiculo,
        Vehiculo.id_usuario == current_user.id_usuario,
        Vehiculo.activo == True
    ).first()

    if not vehiculo:
        raise HTTPException(
            status_code=404,
            detail="El vehículo no existe o no te pertenece"
        )

    # ✅ VALIDACIÓN 2: Límite por Usuario (Un solo incidente activo a la vez)
    incidente_activo = db.query(Incidente).filter(
        Incidente.id_usuario == current_user.id_usuario,
        Incidente.id_estado.in_([1, 2])  # 1: pendiente, 2: en_proceso
    ).first()

    if incidente_activo:
        raise HTTPException(
            status_code=400,
            detail="Ya tienes una emergencia en curso. Por favor, espera a que finalice o cancélala antes de reportar otra."
        )

    # ✅ CREAR INCIDENTE
    nuevo_incidente = Incidente(
        id_usuario=current_user.id_usuario,  # 🔒 Del JWT, no es modificable
        id_vehiculo=incidente_in.id_vehiculo,
        id_estado=1,  # 🔒 Siempre inicia en "pendiente"
        descripcion_usuario=incidente_in.descripcion_usuario,
        latitud=incidente_in.latitud,
        longitud=incidente_in.longitud,
        # id_categoria y id_prioridad se quedan NULL, la IA los llena después
    )

    db.add(nuevo_incidente)
    db.flush()  # obtener id_incidente antes del commit

    # Auto-registrar métrica con fecha_inicio
    from datetime import datetime, timezone
    metrica = Metrica(
        id_incidente=nuevo_incidente.id_incidente,
        fecha_inicio=datetime.now(timezone.utc),
    )
    db.add(metrica)
    db.commit()
    db.refresh(nuevo_incidente)

    return nuevo_incidente


@router.get(
    "/mis-incidencias",
    response_model=List[IncidenteDetalle],
    summary="Listar mis incidencias",
    description="Retorna incidencias del usuario con filtros opcionales por estado y fecha"
)
def listar_mis_incidencias(
    estado: Optional[str] = Query(None, description="Filtrar por nombre de estado: pendiente|en_proceso|atendido|cancelado"),
    desde: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que Flutter obtenga el historial de incidencias del usuario.
    
    Filtros opcionales:
    - estado: nombre del estado (pendiente, en_proceso, atendido, cancelado)
    - desde: fecha inicial (YYYY-MM-DD)
    - hasta: fecha final (YYYY-MM-DD)
    
    Solo retorna incidencias que le pertenecen (id_usuario = current_user.id_usuario)
    Ordenadas por fecha (más reciente primero)
    """
    q = db.query(Incidente).filter(Incidente.id_usuario == current_user.id_usuario)
    
    # Filtrar por estado si se proporciona
    if estado:
        q = q.join(EstadoIncidente).filter(EstadoIncidente.nombre == estado)
    
    # Filtrar por rango de fechas
    if desde:
        from datetime import datetime
        q = q.filter(Incidente.created_at >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        from datetime import datetime
        q = q.filter(Incidente.created_at <= datetime.combine(hasta, datetime.max.time()))
    
    incidencias = q.order_by(Incidente.created_at.desc()).all()
    if incidencias:
        ids = [inc.id_incidente for inc in incidencias]
        evaluados = {
            row[0]
            for row in db.query(Evaluacion.id_incidente)
            .filter(Evaluacion.id_incidente.in_(ids))
            .all()
        }
        for inc in incidencias:
            setattr(inc, "evaluado", inc.id_incidente in evaluados)

    return incidencias


@router.post(
    "/{id_incidente}/analizar-ia",
    response_model=IncidenteDetalle,
    summary="Clasificar incidente con IA (Bedrock Claude)",
    description="Analiza evidencias y descripcion con Claude Sonnet 4.5 y rellena categoria, prioridad y resumen."
)
def analizar_incidente_con_ia(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()

    if not incidente:
        raise HTTPException(
            status_code=404,
            detail="Incidencia no encontrada o no tienes permiso",
        )

    try:
        clasificar_incidente(db, incidente)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error en el servicio de IA: {e}",
        )

    return incidente


class CambiarTallerRequest(BaseModel):
    id_candidato: int = Field(..., description="ID del candidato de asignacion a seleccionar")


class TecnicoUbicacionResponse(BaseModel):
    id_incidente: int
    id_asignacion: int
    id_tecnico: int
    nombre_tecnico: str
    estado_asignacion: str
    latitud_tecnico: float
    longitud_tecnico: float


@router.put(
    "/{id_incidente}/cambiar-taller",
    response_model=IncidenteDetalle,
    summary="Cambiar el taller seleccionado de un incidente",
    description="Permite al cliente elegir otro taller entre los candidatos generados por el motor de asignacion."
)
def cambiar_taller(
    id_incidente: int,
    payload: CambiarTallerRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()
    if not incidente:
        raise HTTPException(
            status_code=404,
            detail="Incidencia no encontrada o no tienes permiso",
        )

    nuevo = db.query(CandidatoAsignacion).filter(
        CandidatoAsignacion.id_candidato == payload.id_candidato,
        CandidatoAsignacion.id_incidente == id_incidente,
    ).first()
    if not nuevo:
        raise HTTPException(
            status_code=404,
            detail="El candidato no existe o no pertenece a esta incidencia",
        )

    db.query(CandidatoAsignacion).filter(
        CandidatoAsignacion.id_incidente == id_incidente
    ).update({CandidatoAsignacion.seleccionado: False}, synchronize_session=False)
    nuevo.seleccionado = True

    asignacion = db.query(Asignacion).filter(
        Asignacion.id_incidente == id_incidente
    ).order_by(Asignacion.created_at.desc()).first()

    if asignacion:
        asignacion.id_taller = nuevo.id_taller
        asignacion.id_usuario = None
    else:
        estado_pendiente = db.query(EstadoAsignacion).filter_by(nombre="pendiente").first()
        id_estado_pendiente = estado_pendiente.id_estado_asignacion if estado_pendiente else 1
        db.add(Asignacion(
            id_incidente=id_incidente,
            id_taller=nuevo.id_taller,
            id_estado_asignacion=id_estado_pendiente,
        ))

    db.commit()
    db.refresh(incidente)
    return incidente


@router.get(
    "/{id_incidente}",
    response_model=IncidenteDetalle,
    summary="Obtener detalle de incidencia",
    description="Retorna los detalles completos de una incidencia específica"
)
def obtener_incidencia(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para que Flutter obtenga los detalles de una incidencia específica.

    Validación de seguridad: Solo puede acceder a sus propias incidencias
    """
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario
    ).first()

    if not incidente:
        raise HTTPException(
            status_code=404,
            detail="Incidencia no encontrada o no tienes permiso para verla"
        )

    evaluado = (
        db.query(Evaluacion.id_incidente)
        .filter(Evaluacion.id_incidente == id_incidente)
        .first()
        is not None
    )
    setattr(incidente, "evaluado", evaluado)
    return incidente


@router.get(
    "/{id_incidente}/tecnico-ubicacion",
    response_model=TecnicoUbicacionResponse,
    summary="Obtener ubicación actual del técnico",
    description="Retorna la posición actual del técnico asignado para que el cliente lo visualice en tiempo real."
)
def obtener_ubicacion_tecnico(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario
    ).first()

    if not incidente:
        raise HTTPException(
            status_code=404,
            detail="Incidencia no encontrada o no tienes permiso para verla"
        )

    asignacion = db.query(Asignacion).filter(
        Asignacion.id_incidente == id_incidente
    ).order_by(Asignacion.updated_at.desc()).first()

    if not asignacion or not asignacion.id_usuario:
        raise HTTPException(
            status_code=404,
            detail="Aún no hay técnico asignado a esta incidencia"
        )

    estado_nombre = (asignacion.estado.nombre if asignacion.estado else "").lower()
    if estado_nombre not in {"aceptada", "en_camino", "completada"}:
        raise HTTPException(
            status_code=404,
            detail="El técnico todavía no está disponible para seguimiento"
        )

    ubicacion = db.query(UsuarioTaller).filter(
        UsuarioTaller.id_usuario == asignacion.id_usuario,
        UsuarioTaller.id_taller == asignacion.id_taller,
        UsuarioTaller.activo == True,
    ).first()

    if not ubicacion or ubicacion.latitud is None or ubicacion.longitud is None:
        raise HTTPException(
            status_code=404,
            detail="El técnico aún no ha compartido su ubicación"
        )

    tecnico = db.query(Usuario).filter(Usuario.id_usuario == asignacion.id_usuario).first()

    return TecnicoUbicacionResponse(
        id_incidente=id_incidente,
        id_asignacion=asignacion.id_asignacion,
        id_tecnico=asignacion.id_usuario,
        nombre_tecnico=(tecnico.nombre if tecnico else "Técnico"),
        estado_asignacion=(asignacion.estado.nombre if asignacion.estado else "desconocido"),
        latitud_tecnico=ubicacion.latitud,
        longitud_tecnico=ubicacion.longitud,
    )


# ============ CANCELAR INCIDENTE ============

@router.patch(
    "/{id_incidente}/cancelar",
    response_model=IncidenteDetalle,
    summary="Cancelar un incidente activo",
    description="El cliente cancela un incidente propio en estado pendiente o en_proceso.",
)
def cancelar_incidente(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.models.incidente import HistorialEstadoIncidente

    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado o no te pertenece")

    estado_actual = db.get(EstadoIncidente, incidente.id_estado)
    if not estado_actual or estado_actual.nombre not in ("pendiente", "en_proceso"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo puedes cancelar incidentes pendientes o en proceso. Estado actual: '{estado_actual.nombre if estado_actual else '?'}'.",
        )

    estado_cancelado = db.query(EstadoIncidente).filter_by(nombre="cancelado").first()
    if not estado_cancelado:
        raise HTTPException(status_code=500, detail="Estado 'cancelado' no encontrado en catálogo")

    db.add(HistorialEstadoIncidente(
        id_incidente=incidente.id_incidente,
        id_estado_anterior=incidente.id_estado,
        id_estado_nuevo=estado_cancelado.id_estado,
        observacion="Cancelado por el cliente",
    ))
    incidente.id_estado = estado_cancelado.id_estado
    db.commit()
    db.refresh(incidente)
    return incidente


# ============ A.3 — CU-10: EVALUAR SERVICIO ============

@router.post(
    "/{id_incidente}/evaluar",
    response_model=EvaluacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluar el servicio recibido",
    description="El cliente califica (1-5 estrellas) el servicio del taller una vez que el incidente está 'atendido'.",
)
def evaluar_servicio(
    id_incidente: int,
    payload: EvaluacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # 1. Verificar ownership del incidente
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()
    if not incidente:
        raise HTTPException(
            status_code=404,
            detail="Incidencia no encontrada o no te pertenece",
        )

    # 2. Solo se puede evaluar un incidente atendido
    estado = db.get(EstadoIncidente, incidente.id_estado)
    if not estado or estado.nombre != "atendido":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Solo puedes evaluar incidentes en estado 'atendido'. "
                f"Estado actual: '{estado.nombre if estado else '?'}'."
            ),
        )

    # 3. No permitir evaluaciones duplicadas
    existente = db.query(Evaluacion).filter_by(id_incidente=id_incidente).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail="Ya evaluaste este servicio",
        )

    # 4. Buscar la asignación completada para vincular taller y técnico
    asignacion_completada = (
        db.query(Asignacion)
        .filter(Asignacion.id_incidente == id_incidente)
        .join(EstadoAsignacion)
        .filter(EstadoAsignacion.nombre == "completada")
        .first()
    )
    if not asignacion_completada:
        raise HTTPException(
            status_code=400,
            detail="No hay asignación completada para este incidente",
        )

    # 5. Crear la evaluación
    evaluacion = Evaluacion(
        id_incidente=id_incidente,
        id_usuario=current_user.id_usuario,
        id_taller=asignacion_completada.id_taller,
        id_tecnico=asignacion_completada.id_usuario,  # ID del usuario técnico
        estrellas=payload.estrellas,
        comentario=payload.comentario,
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion
