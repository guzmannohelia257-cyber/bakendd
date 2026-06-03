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
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.db.session import get_db
from app.models.usuario import Usuario, Vehiculo
from app.models.usuario_taller import UsuarioTaller
from app.models.incidente import Incidente, Asignacion, CandidatoAsignacion, Evaluacion
from app.models.ubicacion import UbicacionTecnico
from app.models.catalogos import CategoriaProblema, Prioridad, EstadoIncidente, EstadoAsignacion
from app.models.transaccional import Metrica
from app.models.taller import Taller
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
from app.core.security import get_current_user, get_current_taller
from app.core.tenant_context import current_tenant
from app.services.ia_service import clasificar_incidente
from app.services import matching_service
from app.services.broadcast_service import (
    broadcast_emergencia,
    broadcast_incidente_tomado,
    notify_cliente_asignado,
)

router = APIRouter(
    prefix="/incidencias",
    tags=["Gestión de Incidencias (CU-06)"],
    responses={
        400: {"description": "Bad Request - Validación fallida"},
        401: {"description": "Unauthorized - Token inválido o expirado"},
        404: {"description": "Not Found - Recurso no encontrado"},
    }
)


# Catálogos (lectura)

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


# Operaciones (crear, listar, obtener)

def _ensure_estado_borrador(db: Session) -> EstadoIncidente:
    """Asegura que el estado 'borrador' exista; lo crea on-the-fly si falta."""
    estado = db.query(EstadoIncidente).filter_by(nombre="borrador").first()
    if not estado:
        estado = EstadoIncidente(
            nombre="borrador",
            descripcion="Borrador: el cliente aún no confirmó el taller",
        )
        db.add(estado)
        db.commit()
        db.refresh(estado)
    return estado


def _borrar_incidentes_y_dependencias(db: Session, ids: list[int]) -> None:
    """
    Borra incidentes + todas sus filas hijas en orden seguro.
    Las FK no tienen ON DELETE CASCADE, así que hay que hacerlo a mano.
    """
    if not ids:
        return
    from app.models.incidente import (
        Asignacion as _Asignacion,
        CandidatoAsignacion as _CandidatoAsignacion,
        Evidencia as _Evidencia,
        HistorialEstadoAsignacion as _HEA,
        HistorialEstadoIncidente as _HEI,
    )
    from app.models.transaccional import (
        Mensaje as _Mensaje,
        Metrica as _Metrica,
        Notificacion as _Notificacion,
        Pago as _Pago,
    )

    asignacion_ids = [
        row[0]
        for row in db.query(_Asignacion.id_asignacion)
        .filter(_Asignacion.id_incidente.in_(ids))
        .all()
    ]
    if asignacion_ids:
        db.query(_HEA).filter(_HEA.id_asignacion.in_(asignacion_ids)).delete(
            synchronize_session=False
        )
    db.query(_HEI).filter(_HEI.id_incidente.in_(ids)).delete(synchronize_session=False)
    db.query(_CandidatoAsignacion).filter(
        _CandidatoAsignacion.id_incidente.in_(ids)
    ).delete(synchronize_session=False)
    db.query(_Asignacion).filter(_Asignacion.id_incidente.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(_Evidencia).filter(_Evidencia.id_incidente.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(_Metrica).filter(_Metrica.id_incidente.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(_Notificacion).filter(_Notificacion.id_incidente.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(_Mensaje).filter(_Mensaje.id_incidente.in_(ids)).delete(
        synchronize_session=False
    )
    db.query(_Pago).filter(_Pago.id_incidente.in_(ids)).delete(synchronize_session=False)
    db.query(Incidente).filter(Incidente.id_incidente.in_(ids)).delete(
        synchronize_session=False
    )
    db.commit()


@router.post(
    "/",
    response_model=IncidenteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un borrador de incidente (no se publica al taller hasta confirmar)",
    description=(
        "Crea el incidente en estado 'borrador'. No se notifica a talleres ni se ejecuta "
        "el motor de asignación hasta que el cliente llama POST /incidencias/{id}/confirmar "
        "tras elegir taller. Soporta `idempotency_key` para deduplicar reintentos "
        "del modo offline."
    ),
)
async def reportar_incidencia(
    incidente_in: IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea el incidente como BORRADOR. El borrador:
    - No aparece en el historial del cliente
    - No cuenta como incidente activo
    - No notifica a talleres
    - Permite subir evidencias y correr IA

    Sólo cuando el cliente confirma un taller (POST /incidencias/{id}/confirmar)
    el incidente pasa a 'pendiente', se ejecuta el motor de asignación y se notifica
    a los talleres compatibles.
    """

    # Idempotencia offline: si llega un key y ya existe un incidente del mismo
    # usuario con ese key, devolvemos el existente sin crear nada nuevo.
    if incidente_in.idempotency_key:
        existente = (
            db.query(Incidente)
            .filter(
                Incidente.id_usuario == current_user.id_usuario,
                Incidente.idempotency_key == incidente_in.idempotency_key,
            )
            .first()
        )
        if existente:
            return existente

    # Validación: solo se permite 1 incidente activo (pendiente/en_proceso) por usuario
    estado_activo_existente = db.query(Incidente).join(
        EstadoIncidente, Incidente.id_estado == EstadoIncidente.id_estado
    ).filter(
        Incidente.id_usuario == current_user.id_usuario,
        EstadoIncidente.nombre.in_(["pendiente", "en_proceso"])
    ).first()
    if estado_activo_existente:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Ya tienes un incidente activo (#{estado_activo_existente.id_incidente}). "
                "Espera a que sea atendido o cancélalo antes de reportar otro."
            ),
        )

    # Vehículo válido y del usuario
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

    estado_borrador = _ensure_estado_borrador(db)

    # Limpia borradores previos del mismo usuario (si abandonó un flujo anterior).
    # Hay que borrar los hijos primero porque las FKs no tienen cascade.
    borradores_previos_ids = [
        row[0]
        for row in db.query(Incidente.id_incidente).filter(
            Incidente.id_usuario == current_user.id_usuario,
            Incidente.id_estado == estado_borrador.id_estado,
        ).all()
    ]
    if borradores_previos_ids:
        _borrar_incidentes_y_dependencias(db, borradores_previos_ids)

    # Crear incidente como borrador (no se notifica a talleres)
    nuevo_incidente = Incidente(
        id_usuario=current_user.id_usuario,
        id_vehiculo=incidente_in.id_vehiculo,
        id_estado=estado_borrador.id_estado,
        descripcion_usuario=incidente_in.descripcion_usuario,
        latitud=incidente_in.latitud,
        longitud=incidente_in.longitud,
        idempotency_key=incidente_in.idempotency_key,
    )
    db.add(nuevo_incidente)
    db.flush()

    from datetime import datetime, timezone
    metrica = Metrica(
        id_incidente=nuevo_incidente.id_incidente,
        fecha_inicio=datetime.now(timezone.utc),
    )
    db.add(metrica)
    db.commit()
    db.refresh(nuevo_incidente)

    # Nota: NO se ejecuta matching_service ni broadcast aquí.
    # El cliente debe confirmar primero el taller via POST /incidencias/{id}/confirmar.
    return nuevo_incidente


class ConfirmarTallerRequest(BaseModel):
    id_taller_preferido: Optional[int] = Field(
        default=None,
        description="ID del taller que el cliente eligió (opcional; si no se manda se hace broadcast a todos los compatibles)",
    )


@router.post(
    "/{id_incidente}/confirmar",
    response_model=IncidenteResponse,
    summary="Confirmar el incidente borrador (taller elegido) y publicarlo",
    description=(
        "Promueve el incidente de 'borrador' a 'pendiente', ejecuta el motor de asignación "
        "y notifica a los talleres compatibles. Es el paso final del flujo de reporte."
    ),
)
async def confirmar_incidencia(
    id_incidente: int,
    payload: Optional[ConfirmarTallerRequest] = None,
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
            detail="Incidente no encontrado o no te pertenece",
        )

    estado_actual = db.get(EstadoIncidente, incidente.id_estado)
    if not estado_actual or estado_actual.nombre != "borrador":
        raise HTTPException(
            status_code=400,
            detail=(
                f"El incidente no está en estado borrador (estado actual: "
                f"'{estado_actual.nombre if estado_actual else '?'}'). "
                "Sólo los borradores pueden confirmarse."
            ),
        )

    estado_pendiente = db.query(EstadoIncidente).filter_by(nombre="pendiente").first()
    if not estado_pendiente:
        raise HTTPException(status_code=500, detail="Estado 'pendiente' no existe en catálogo")

    # Promover a pendiente + registrar historial
    from app.models.incidente import HistorialEstadoIncidente
    db.add(HistorialEstadoIncidente(
        id_incidente=incidente.id_incidente,
        id_estado_anterior=incidente.id_estado,
        id_estado_nuevo=estado_pendiente.id_estado,
        observacion="Cliente confirmó taller, incidente publicado",
    ))
    incidente.id_estado = estado_pendiente.id_estado
    db.commit()
    db.refresh(incidente)

    # Motor de asignación: lista talleres compatibles + crea candidatos
    talleres_dist = matching_service.buscar_talleres_compatibles(db, incidente)
    talleres = [t for t, _d in talleres_dist]
    id_taller_destino: Optional[int] = None
    if talleres:
        matching_service.crear_candidatos(db, incidente, talleres_dist)

        # Determinar el taller "destinatario" de la asignación pendiente:
        # 1. Si el cliente eligió taller -> ese
        # 2. Si no, el primer candidato (más cercano)
        if payload and payload.id_taller_preferido:
            if any(t.id_taller == payload.id_taller_preferido for t in talleres):
                id_taller_destino = payload.id_taller_preferido
        if id_taller_destino is None:
            id_taller_destino = talleres[0].id_taller

        # Marcar el candidato como seleccionado para trazabilidad
        cand = db.query(CandidatoAsignacion).filter(
            CandidatoAsignacion.id_incidente == incidente.id_incidente,
            CandidatoAsignacion.id_taller == id_taller_destino,
        ).first()
        if cand:
            cand.seleccionado = True

        # Crear la asignación en estado pendiente para que aparezca en el
        # dashboard del taller. Si ese taller rechaza, el endpoint de rechazo
        # se encarga de pasar al siguiente candidato.
        estado_asig_pendiente = db.query(EstadoAsignacion).filter_by(nombre="pendiente").first()
        if estado_asig_pendiente:
            taller_destino = next(t for t in talleres if t.id_taller == id_taller_destino)
            db.add(Asignacion(
                id_tenant=taller_destino.id_tenant,
                id_incidente=incidente.id_incidente,
                id_taller=id_taller_destino,
                id_estado_asignacion=estado_asig_pendiente.id_estado_asignacion,
            ))
            # El incidente hereda el tenant del taller para que aparezca en sus queries
            incidente.id_tenant = taller_destino.id_tenant
        db.commit()
        db.refresh(incidente)

        await broadcast_emergencia(incidente, talleres)

    return incidente


@router.delete(
    "/{id_incidente}/borrador",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Descartar el borrador (cliente abandonó el flujo)",
    description=(
        "Borra un incidente que aún está en estado 'borrador'. Se usa cuando el cliente "
        "sale de la pantalla de selección de taller sin confirmar."
    ),
)
def descartar_borrador(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()
    if not incidente:
        # Idempotente: si no existe, devolvemos 204 igualmente
        return

    estado = db.get(EstadoIncidente, incidente.id_estado)
    if not estado or estado.nombre != "borrador":
        raise HTTPException(
            status_code=400,
            detail="Sólo se pueden descartar incidentes en estado borrador",
        )

    _borrar_incidentes_y_dependencias(db, [incidente.id_incidente])
    return


@router.post(
    "/{id_incidente}/aceptar",
    summary="Taller acepta una emergencia entrante; primero gana",
)
async def aceptar_emergencia(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    token = current_tenant.set(0)
    try:
        inc: Incidente | None = (
            db.execute(
                select(Incidente)
                .where(Incidente.id_incidente == id_incidente)
                .with_for_update()
            ).scalar_one_or_none()
        )
        if not inc:
            raise HTTPException(404, "Incidente no existe")

        cand = (
            db.query(CandidatoAsignacion)
            .filter_by(id_incidente=id_incidente, id_taller=current_taller.id_taller)
            .first()
        )
        if not cand:
            raise HTTPException(403, "Tu taller no fue convocado a esta emergencia")

        estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").one()
        estado_pendiente = db.query(EstadoAsignacion).filter_by(nombre="pendiente").first()

        # Hay tres casos:
        # 1. Ya existe asignación pendiente para ESTE taller (creada por
        #    /confirmar tras la elección del cliente) -> la transicionamos
        #    a 'aceptada'.
        # 2. Ya existe asignación en otro estado (aceptada, en_camino, etc.)
        #    -> 409, ya fue tomada por otro.
        # 3. No existe asignación -> creamos una nueva en 'aceptada' (flujo
        #    legado: el taller toma el broadcast sin confirmación previa).
        existing = db.query(Asignacion).filter_by(id_incidente=id_incidente).first()
        if existing:
            es_de_este_taller = existing.id_taller == current_taller.id_taller
            es_pendiente = (
                estado_pendiente is not None
                and existing.id_estado_asignacion == estado_pendiente.id_estado_asignacion
            )
            if es_de_este_taller and es_pendiente:
                # Caso 1: promovemos la pendiente a aceptada.
                existing.id_estado_asignacion = estado_aceptada.id_estado_asignacion
                asig = existing
            else:
                # Caso 2: ya tomada por otro o en otro estado terminal.
                raise HTTPException(
                    409,
                    f"Esta emergencia ya fue tomada por el taller {existing.id_taller}",
                )
        else:
            # Caso 3: aceptación directa sin confirmación previa del cliente.
            asig = Asignacion(
                id_tenant=current_taller.id_tenant,
                id_incidente=id_incidente,
                id_taller=current_taller.id_taller,
                id_estado_asignacion=estado_aceptada.id_estado_asignacion,
            )
            db.add(asig)

        cand.seleccionado = True
        inc.id_tenant = current_taller.id_tenant

        db.commit()
        db.refresh(asig)

        perdedores_q = (
            db.query(Taller)
            .join(CandidatoAsignacion, CandidatoAsignacion.id_taller == Taller.id_taller)
            .filter(
                CandidatoAsignacion.id_incidente == id_incidente,
                CandidatoAsignacion.id_taller != current_taller.id_taller,
            )
            .all()
        )
        await broadcast_incidente_tomado(inc, current_taller, perdedores_q)
        await notify_cliente_asignado(inc, current_taller, asig)
    finally:
        current_tenant.reset(token)

    return {
        "id_asignacion": asig.id_asignacion,
        "id_taller": current_taller.id_taller,
        "nuevo_estado": "aceptada",
    }


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

    # Filtrar por estado si se proporciona; si no, excluir 'borrador' siempre
    if estado:
        q = q.join(EstadoIncidente).filter(EstadoIncidente.nombre == estado)
    else:
        q = q.join(EstadoIncidente).filter(EstadoIncidente.nombre != "borrador")
    
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
    distancia_km: Optional[float] = None
    eta_minutos: Optional[int] = None


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
async def obtener_ubicacion_tecnico(
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
    if estado_nombre not in {"aceptada", "en_camino", "llegado", "completada"}:
        raise HTTPException(
            status_code=404,
            detail="El técnico todavía no está disponible para seguimiento"
        )

    # Fuente unica del ETA: la ultima fila UbicacionTecnico de esta asignacion
    # (la misma que usa GET /asignaciones/{id}/eta). Fallback a UsuarioTaller si
    # el tecnico todavia no ha emitido ninguna UbicacionTecnico.
    ultimo = (
        db.query(UbicacionTecnico)
        .filter(UbicacionTecnico.id_asignacion == asignacion.id_asignacion)
        .order_by(UbicacionTecnico.created_at.desc())
        .first()
    )

    if ultimo:
        lat_tec = ultimo.latitud
        lng_tec = ultimo.longitud
    else:
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

        lat_tec = ubicacion.latitud
        lng_tec = ubicacion.longitud

    tecnico = db.query(Usuario).filter(Usuario.id_usuario == asignacion.id_usuario).first()

    # Distancia/ETA con OSRM (el MISMO calculo que ve el tecnico y el cliente en
    # vivo), para que el tiempo/distancia sea consistente en todas las vistas.
    from app.services import tracking_service

    dist_km, eta_seg = await tracking_service.calcular_eta(
        lat_tec, lng_tec,
        incidente.latitud, incidente.longitud,
    )

    return TecnicoUbicacionResponse(
        id_incidente=id_incidente,
        id_asignacion=asignacion.id_asignacion,
        id_tecnico=asignacion.id_usuario,
        nombre_tecnico=(tecnico.nombre if tecnico else "Técnico"),
        estado_asignacion=(asignacion.estado.nombre if asignacion.estado else "desconocido"),
        latitud_tecnico=lat_tec,
        longitud_tecnico=lng_tec,
        distancia_km=round(dist_km, 2),
        eta_minutos=round(eta_seg / 60),
    )


# Cancelar incidente

@router.patch(
    "/{id_incidente}/cancelar",
    response_model=IncidenteDetalle,
    summary="Cancelar un incidente activo",
    description=(
        "El cliente cancela un incidente propio en estado pendiente o en_proceso. "
        "Si la asignacion ya esta 'en_camino' se crea automaticamente un Pago de "
        "tipo 'penalizacion' (tarifa fija USD 5)."
    ),
)
def cancelar_incidente(
    id_incidente: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.models.incidente import HistorialEstadoIncidente
    from app.services import pago_service

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

    # Penalización automática si la asignación activa está 'en_camino' o 'llegado'
    # (en ambos casos el técnico ya salió/llegó al sitio).
    pago_penalizacion = None
    try:
        from app.models.catalogos import EstadoAsignacion

        ids_penalizables = [
            row[0]
            for row in db.query(EstadoAsignacion.id_estado_asignacion).filter(
                EstadoAsignacion.nombre.in_(["en_camino", "llegado"])
            ).all()
        ]
        if ids_penalizables:
            asig_en_camino = (
                db.query(Asignacion)
                .filter(
                    Asignacion.id_incidente == incidente.id_incidente,
                    Asignacion.id_estado_asignacion.in_(ids_penalizables),
                )
                .first()
            )
            if asig_en_camino:
                pago_penalizacion = pago_service.penalizar_por_cancelacion(
                    db, incidente
                )
    except Exception:
        # No bloquear la cancelación si el cobro falla; se registra en logs.
        pago_penalizacion = None

    db.add(HistorialEstadoIncidente(
        id_incidente=incidente.id_incidente,
        id_estado_anterior=incidente.id_estado,
        id_estado_nuevo=estado_cancelado.id_estado,
        observacion=(
            "Cancelado por el cliente (con penalizacion)"
            if pago_penalizacion
            else "Cancelado por el cliente"
        ),
    ))
    incidente.id_estado = estado_cancelado.id_estado
    db.commit()
    db.refresh(incidente)
    return incidente


# A.3 — CU-10: Evaluar servicio

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
    # 1. Verificar que el incidente pertenezca al usuario actual
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
        estrellas=payload.estrellas,
        comentario=payload.comentario,
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion
