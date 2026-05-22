"""
Router del Técnico.

El Técnico es un USUARIO (tabla usuario, id_rol=3) que se autentica normalmente.
Desde la app móvil (Flutter) usa POST /usuarios/login con sus credenciales.

Endpoints:
  GET /tecnicos/asignacion-actual                      → asignación activa
  PUT /tecnicos/mi-ubicacion                           → actualizar ubicación GPS en tiempo real
  GET /tecnicos/mis-asignaciones/{id}/evidencias       → ver evidencias del incidente
  PUT /tecnicos/mis-asignaciones/{id}/iniciar-viaje    → aceptada → en_camino
  PUT /tecnicos/mis-asignaciones/{id}/completar        → en_camino → completada
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user_model import Usuario
from app.models.taller import Taller
from app.models.incidente import Asignacion, HistorialEstadoAsignacion, Incidente, Evidencia
from app.models.ubicacion import UbicacionTecnico
from app.models.usuario_taller import UsuarioTaller
from app.models.catalogos import EstadoAsignacion, EstadoIncidente
from app.schemas.taller_schema import (
    TecnicoAsignacionResponse, IniciarViajeRequest, CompletarAsignacionRequest,
    UbicacionTecnicoRequest, EvidenciaMiniT, MensajeResponse
)
from app.schemas.tecnico_schema import (
    CambiarTallerResponse,
    TallerActivoInfo,
    TallerPublicoMini,
    TecnicoLoginConTallerRequest,
    TecnicoLoginResponse,
    UsuarioMini,
)
from app.schemas.tracking_schema import UbicacionPing
from app.core.security import create_access_token, get_current_user, verify_password
from app.core.tenant_context import current_tenant
from app.services.trazabilidad import cambiar_estado_asignacion, cambiar_estado_incidente
from app.services.notificacion_service import crear_y_enviar_notificacion
from app.services import tracking_service
from app.services.notify_service import notify_incidente

router = APIRouter(
    prefix="/tecnicos",
    tags=["Gestión de Técnicos (app móvil)"],
    responses={
        401: {"description": "No autorizado - Token inválido o usuario no es técnico"},
        403: {"description": "Prohibido - Usuario no es técnico"},
        404: {"description": "No encontrado - Sin asignaciones activas"},
    },
)


# ============================================================
# M9 — Login multi-taller del tecnico (PRE-LOGIN selector)
# ============================================================

@router.get(
    "/talleres-publicos",
    response_model=List[TallerPublicoMini],
    summary="Lista publica de talleres (selector pre-login del tecnico)",
)
def talleres_publicos(db: Session = Depends(get_db)):
    """
    Endpoint PUBLICO (sin auth). Devuelve info no sensible de talleres activos
    para que la app movil del tecnico pueda mostrar el selector ANTES del login.
    """
    # Bypass del filtro tenant: no hay contexto al ser pre-login
    tok = current_tenant.set(0)
    try:
        return (
            db.query(Taller)
            .filter(Taller.activo.is_(True))
            .order_by(Taller.nombre)
            .all()
        )
    finally:
        current_tenant.reset(tok)


@router.post(
    "/login",
    response_model=TecnicoLoginResponse,
    summary="Login del tecnico contra un taller especifico",
)
def login_tecnico(body: TecnicoLoginConTallerRequest, db: Session = Depends(get_db)):
    """
    Valida:
      1. email+password contra tabla usuario.
      2. usuario.id_rol == 3 (tecnico).
      3. existe UsuarioTaller activo entre este usuario y el id_taller indicado.
    Emite JWT con `id_tenant` del taller -> filtro tenant aplica automaticamente.
    """
    # Bypass tenant para localizar usuario y vinculo (sin contexto previo)
    tok = current_tenant.set(0)
    try:
        usuario = db.query(Usuario).filter(Usuario.email == body.email).first()
        if not usuario or not verify_password(body.password, usuario.password_hash):
            raise HTTPException(401, "Credenciales invalidas")
        if usuario.id_rol != 3:
            raise HTTPException(403, "Esta cuenta no es de tecnico")
        if not usuario.activo:
            raise HTTPException(403, "Cuenta desactivada")

        vinculo = (
            db.query(UsuarioTaller)
            .join(Taller, Taller.id_taller == UsuarioTaller.id_taller)
            .filter(
                UsuarioTaller.id_usuario == usuario.id_usuario,
                UsuarioTaller.id_taller == body.id_taller,
                UsuarioTaller.activo.is_(True),
            )
            .first()
        )
        if not vinculo:
            raise HTTPException(403, "No estas vinculado a este taller")

        taller = vinculo.taller
    finally:
        current_tenant.reset(tok)

    token = create_access_token(
        subject_id=usuario.id_usuario,
        tipo="usuario",
        extra_claims={
            "id_tenant": taller.id_tenant,
            "id_taller_activo": taller.id_taller,
        },
    )
    return TecnicoLoginResponse(
        access_token=token,
        usuario=UsuarioMini(
            id_usuario=usuario.id_usuario,
            nombre=usuario.nombre,
            email=usuario.email,
        ),
        taller_activo=TallerActivoInfo(
            id_taller=taller.id_taller,
            id_tenant=taller.id_tenant,
            nombre=taller.nombre,
        ),
    )


@router.post(
    "/me/cambiar-taller/{id_taller}",
    response_model=CambiarTallerResponse,
    summary="Tecnico cambia taller activo sin reloguearse",
)
def cambiar_taller_activo(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Permite al tecnico moverse entre talleres a los que esta vinculado sin
    re-loguearse. Devuelve un nuevo JWT con el `id_tenant` del taller elegido.
    """
    if current_user.id_rol != 3:
        raise HTTPException(403, "Solo tecnicos pueden cambiar taller activo")

    tok = current_tenant.set(0)
    try:
        vinculo = (
            db.query(UsuarioTaller)
            .join(Taller, Taller.id_taller == UsuarioTaller.id_taller)
            .filter(
                UsuarioTaller.id_usuario == current_user.id_usuario,
                UsuarioTaller.id_taller == id_taller,
                UsuarioTaller.activo.is_(True),
            )
            .first()
        )
    finally:
        current_tenant.reset(tok)

    if not vinculo:
        raise HTTPException(404, "No estas vinculado a ese taller")

    taller = vinculo.taller
    token = create_access_token(
        subject_id=current_user.id_usuario,
        tipo="usuario",
        extra_claims={
            "id_tenant": taller.id_tenant,
            "id_taller_activo": taller.id_taller,
        },
    )
    return CambiarTallerResponse(
        access_token=token,
        taller_activo=TallerActivoInfo(
            id_taller=taller.id_taller,
            id_tenant=taller.id_tenant,
            nombre=taller.nombre,
        ),
    )


# ============================================================
# Endpoints existentes (protegidos)
# ============================================================

@router.get(
    "/asignacion-actual",
    response_model=TecnicoAsignacionResponse,
    summary="Obtener asignación activa del técnico",
    description="Retorna la asignación activa del técnico (estado 'aceptada' o 'en_camino'). Requiere ser un usuario con rol de técnico (id_rol=3).",
)
def obtener_asignacion_actual(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar que el usuario es técnico (rol=3)
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con rol técnico pueden acceder a este endpoint",
        )
    
    # Buscar asignaciones activas del técnico (id_usuario)
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_usuario == current_user.id_usuario,
        Asignacion.id_estado_asignacion.in_(
            db.query(EstadoAsignacion.id_estado_asignacion).filter(
                EstadoAsignacion.nombre.in_(["aceptada", "en_camino"])
            )
        ),
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes asignaciones activas en este momento",
        )

    return asignacion


# ============ UBICACIÓN EN TIEMPO REAL ============

@router.put(
    "/mi-ubicacion",
    response_model=MensajeResponse,
    summary="Actualizar ubicación GPS del técnico",
    description="El técnico reporta su posición actual. Se guarda en usuario_taller para que el taller y el cliente puedan verla.",
)
def actualizar_ubicacion(
    payload: UbicacionTecnicoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )

    vinculo = db.query(UsuarioTaller).filter(
        UsuarioTaller.id_usuario == current_user.id_usuario,
        UsuarioTaller.activo == True,
    ).first()

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes vínculo activo con ningún taller",
        )

    vinculo.latitud = payload.latitud
    vinculo.longitud = payload.longitud
    db.commit()

    return {"mensaje": f"Ubicación actualizada: {payload.latitud}, {payload.longitud}"}


@router.post(
    "/me/ubicacion",
    summary="Tecnico envia su ubicacion actual (cada 10-15s mientras va en viaje)",
)
async def reportar_ubicacion(
    body: UbicacionPing,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(403, "Solo tecnicos pueden reportar ubicacion")

    # M9: usar id_tenant del JWT (taller activo elegido al login),
    # NO `.first()` arbitrario. Si el token no trae tenant, el tecnico debe
    # re-loguearse via POST /tecnicos/login con id_taller.
    tid = current_tenant.get()
    if tid is None:
        raise HTTPException(
            400,
            "Token sin id_tenant. Vuelve a iniciar sesion via POST /tecnicos/login indicando id_taller.",
        )

    vinculo = (
        db.query(UsuarioTaller)
        .join(Taller, Taller.id_taller == UsuarioTaller.id_taller)
        .filter(
            UsuarioTaller.id_usuario == current_user.id_usuario,
            Taller.id_tenant == tid,
            UsuarioTaller.activo.is_(True),
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(403, "Tu token no corresponde a un taller donde trabajes activamente")

    vinculo.latitud = body.latitud
    vinculo.longitud = body.longitud

    asig: Asignacion | None = None
    if body.id_asignacion:
        asig = db.query(Asignacion).get(body.id_asignacion)
        if not asig or asig.id_taller != vinculo.id_taller:
            raise HTTPException(403, "Esa asignacion no es de tu taller")

        db.add(
            UbicacionTecnico(
                id_tenant=vinculo.taller.id_tenant,
                id_usuario=current_user.id_usuario,
                id_asignacion=asig.id_asignacion,
                latitud=body.latitud,
                longitud=body.longitud,
                accuracy_m=body.accuracy_m,
                velocidad_kmh=body.velocidad_kmh,
            )
        )

    db.commit()

    eta_resp = None
    llegado_auto = False
    if asig:
        incidente = db.query(Incidente).get(asig.id_incidente)

        dist_km, eta_seg = await tracking_service.calcular_eta(
            body.latitud, body.longitud, incidente.latitud, incidente.longitud
        )
        eta_resp = {
            "distancia_km": round(dist_km, 2),
            "eta_segundos": eta_seg,
            "eta_minutos": round(eta_seg / 60),
        }

        await notify_incidente(
            asig.id_incidente,
            "tecnico.posicion",
            {
                "id_asignacion": asig.id_asignacion,
                "latitud": body.latitud,
                "longitud": body.longitud,
                "eta": eta_resp,
            },
        )

        if tracking_service.llego_geofence(
            body.latitud, body.longitud, incidente.latitud, incidente.longitud
        ) and asig.estado.nombre in ("aceptada", "en_camino"):
            estado_llegado = db.query(EstadoAsignacion).filter_by(nombre="llegado").first()
            if estado_llegado:
                db.add(
                    HistorialEstadoAsignacion(
                        id_asignacion=asig.id_asignacion,
                        id_estado_anterior=asig.id_estado_asignacion,
                        id_estado_nuevo=estado_llegado.id_estado_asignacion,
                        observacion="Auto: geofencing (radio 100m)",
                    )
                )
                asig.id_estado_asignacion = estado_llegado.id_estado_asignacion
                db.commit()
                llegado_auto = True
                await notify_incidente(
                    asig.id_incidente,
                    "asignacion.llegado",
                    {"id_asignacion": asig.id_asignacion},
                )

    return {"ok": True, "eta": eta_resp, "llegado_auto": llegado_auto}


# ============ EVIDENCIAS ============

@router.get(
    "/mis-asignaciones/{id_asignacion}/evidencias",
    response_model=List[EvidenciaMiniT],
    summary="Ver evidencias del incidente",
    description="Lista todas las evidencias (fotos, audios, texto) que el cliente subió al reportar el incidente.",
)
def listar_evidencias(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )

    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_usuario == current_user.id_usuario,
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no asignada a ti",
        )

    evidencias = db.query(Evidencia).filter(
        Evidencia.id_incidente == asignacion.id_incidente
    ).all()

    return evidencias


# ============ A.2 — CU-20: TRANSICIONES EN_CAMINO Y COMPLETADA ============

@router.put(
    "/mis-asignaciones/{id_asignacion}/iniciar-viaje",
    response_model=TecnicoAsignacionResponse,
    summary="Técnico sale hacia el cliente (aceptada → en_camino)",
    description="Marca que el técnico salió hacia el incidente. Requiere rol=3 (técnico).",
)
def iniciar_viaje(
    id_asignacion: int,
    payload: IniciarViajeRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar rol técnico
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )
    
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_usuario == current_user.id_usuario,
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no asignada a ti",
        )

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if not estado_actual or estado_actual.nombre != "aceptada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La asignación está en '{estado_actual.nombre if estado_actual else '?'}', "
                f"solo se puede iniciar viaje desde 'aceptada'"
            ),
        )

    try:
        cambiar_estado_asignacion(
            db, asignacion, "en_camino",
            observacion=f"Técnico {current_user.id_usuario} ({current_user.nombre}) en camino",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Sincronizar estado del incidente: cualquier estado (excepto terminal) → en_proceso
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        estado_inc_actual = db.get(EstadoIncidente, incidente.id_estado)
        if estado_inc_actual and estado_inc_actual.nombre not in ["atendido", "cancelado"]:
            try:
                cambiar_estado_incidente(
                    db, incidente, "en_proceso",
                    observacion=f"Técnico {current_user.nombre} en camino",
                )
            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))

    db.commit()
    db.refresh(asignacion)
    return asignacion


@router.put(
    "/mis-asignaciones/{id_asignacion}/completar",
    response_model=TecnicoAsignacionResponse,
    summary="Servicio completado (en_camino → completada)",
    description="Marca el servicio como completado. Requiere rol=3 (técnico).",
)
def completar_asignacion(
    id_asignacion: int,
    payload: CompletarAsignacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Verificar rol técnico
    if current_user.id_rol != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo técnicos pueden usar este endpoint",
        )
    
    asignacion = db.query(Asignacion).filter(
        Asignacion.id_asignacion == id_asignacion,
        Asignacion.id_usuario == current_user.id_usuario,
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada o no asignada a ti",
        )

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if not estado_actual or estado_actual.nombre != "en_camino":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La asignación está en '{estado_actual.nombre if estado_actual else '?'}', "
                f"solo se puede completar desde 'en_camino'"
            ),
        )

    if payload.costo_final is not None:
        asignacion.costo_estimado = payload.costo_final
    if payload.resumen_trabajo is not None:
        prev = asignacion.nota_taller or ""
        asignacion.nota_taller = f"{prev}\n[TRABAJO] {payload.resumen_trabajo}".strip()

    try:
        cambiar_estado_asignacion(
            db, asignacion, "completada",
            observacion=payload.resumen_trabajo or "Servicio completado por técnico",
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Cerrar el incidente: cualquier estado activo → atendido
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        estado_inc_actual = db.get(EstadoIncidente, incidente.id_estado)
        if estado_inc_actual and estado_inc_actual.nombre not in ["atendido", "cancelado"]:
            try:
                cambiar_estado_incidente(
                    db, incidente, "atendido",
                    observacion=f"Técnico {current_user.nombre} completó el servicio",
                )
            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Notificar al cliente que ya hay un nuevo pago/cobro para revisar
        try:
            cliente = db.get(Usuario, incidente.id_usuario) if incidente.id_usuario else None
            if payload.costo_final is not None:
                mensaje = (
                    f"Tu servicio fue completado. Nuevo pago: Q {payload.costo_final:.2f}. "
                    "Revisa y realiza el pago en la app."
                )
            else:
                mensaje = "Tu servicio fue completado. Tienes un nuevo pago pendiente por revisar."

            crear_y_enviar_notificacion(
                db,
                titulo="Nuevo pago disponible",
                mensaje=mensaje,
                id_usuario=incidente.id_usuario,
                id_incidente=incidente.id_incidente,
                push_token=cliente.push_token if cliente else None,
                data={
                    "tipo": "nuevo_pago",
                    "id_incidente": str(incidente.id_incidente),
                    "id_asignacion": str(asignacion.id_asignacion),
                },
            )
        except Exception:
            # La notificación no debe romper el flujo crítico de cierre
            pass

        # Notificar al cliente para activar flujo de reseña/calificación del taller
        try:
            crear_y_enviar_notificacion(
                db,
                titulo="Califica tu servicio",
                mensaje="Tu servicio finalizó. Cuéntanos tu experiencia y califica al taller.",
                id_usuario=incidente.id_usuario,
                id_incidente=incidente.id_incidente,
                push_token=cliente.push_token if cliente else None,
                data={
                    "tipo": "solicitar_resena",
                    "accion": "calificar_taller",
                    "id_incidente": str(incidente.id_incidente),
                    "id_asignacion": str(asignacion.id_asignacion),
                },
            )
        except Exception:
            # La notificación no debe romper el flujo crítico de cierre
            pass

    db.commit()
    db.refresh(asignacion)
    return asignacion
