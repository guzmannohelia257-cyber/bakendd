"""
Router de Administrador.

Todos los endpoints requieren un usuario con id_rol=4 (admin).
El admin gestiona los talleres y consulta las ganancias de la plataforma.

Endpoints:
  GET    /admin/talleres                   → listar talleres (filtros: activo, verificado, buscar)
  POST   /admin/talleres                   → registrar nuevo taller
  GET    /admin/talleres/{id}              → detalle de un taller con estadísticas
  PATCH  /admin/talleres/{id}/verificar    → activar/desactivar verificación
  DELETE /admin/talleres/{id}              → baja lógica del taller
  GET    /admin/ganancias/mensual          → ganancias de la plataforma por mes
  GET    /admin/ganancias/por-taller       → comisión por taller con rating
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import List, Optional

from app.db.session import get_db
from app.models.taller import Taller, TallerServicio
from app.models.user_model import Usuario
from app.models.incidente import Asignacion, Evaluacion
from app.models.transaccional import Pago
from app.models.catalogos import EstadoAsignacion, EstadoPago, CategoriaProblema
from app.core.security import get_current_admin, hash_password
from app.services.notificacion_service import crear_y_enviar_notificacion
from app.schemas.admin_schema import (
    TallerAdminCreate,
    TallerAdminResponse,
    TallerAdminStatsResponse,
    GananciaMensualRow,
    GananciaMensualResponse,
    GananciaTallerRow,
    GananciaPorTallerResponse,
    CategoriaAdminCreate,
    CategoriaAdminResponse,
)

router = APIRouter(
    prefix="/admin",
    tags=["Administración"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Requiere rol de administrador"},
    },
)

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_taller_or_404(db: Session, id_taller: int) -> Taller:
    taller = db.get(Taller, id_taller)
    if not taller:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    return taller


def _eval_map(db: Session) -> dict:
    """Retorna {id_taller: (promedio_estrellas, total_evaluaciones)}."""
    rows = (
        db.query(
            Evaluacion.id_taller,
            func.avg(Evaluacion.estrellas).label("promedio"),
            func.count(Evaluacion.id_evaluacion).label("total"),
        )
        .group_by(Evaluacion.id_taller)
        .all()
    )
    return {r.id_taller: (r.promedio, r.total) for r in rows}


def _subq_asig_completada(db: Session):
    """Subquery: id_incidente → id_taller para asignaciones completadas."""
    return (
        db.query(
            Asignacion.id_incidente.label("id_incidente"),
            Asignacion.id_taller.label("id_taller"),
        )
        .join(EstadoAsignacion, EstadoAsignacion.id_estado_asignacion == Asignacion.id_estado_asignacion)
        .filter(EstadoAsignacion.nombre == "completada")
        .subquery("asig_comp")
    )


# ── CATEGORÍAS ───────────────────────────────────────────────────────────────

@router.get(
    "/categorias",
    response_model=List[CategoriaAdminResponse],
    summary="Listar todas las categorías de problemas",
)
def listar_categorias(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return db.query(CategoriaProblema).order_by(CategoriaProblema.id_categoria).all()


@router.post(
    "/categorias",
    response_model=CategoriaAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva categoría de problema",
)
def crear_categoria(
    payload: CategoriaAdminCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    nombre_norm = payload.nombre.strip().lower()
    if db.query(CategoriaProblema).filter(CategoriaProblema.nombre == nombre_norm).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una categoría con el nombre '{payload.nombre}'",
        )
    nueva = CategoriaProblema(nombre=nombre_norm, descripcion=payload.descripcion)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


# ── TALLERES ──────────────────────────────────────────────────────────────────

@router.get(
    "/talleres",
    response_model=List[TallerAdminResponse],
    summary="Listar todos los talleres",
)
def listar_talleres(
    activo: Optional[bool] = Query(None, description="Filtrar por activo/inactivo"),
    verificado: Optional[bool] = Query(None, description="Filtrar por verificado"),
    buscar: Optional[str] = Query(None, description="Buscar por nombre o email"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(Taller)

    if activo is not None:
        q = q.filter(Taller.activo == activo)
    if verificado is not None:
        q = q.filter(Taller.verificado == verificado)
    if buscar:
        like = f"%{buscar.strip()}%"
        q = q.filter((Taller.nombre.ilike(like)) | (Taller.email.ilike(like)))

    return q.order_by(Taller.created_at.desc()).all()


@router.post(
    "/talleres",
    response_model=TallerAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo taller",
)
def crear_taller(
    payload: TallerAdminCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    if db.query(Taller).filter(Taller.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un taller con ese email",
        )

    taller = Taller(
        nombre=payload.nombre,
        email=payload.email,
        password_hash=hash_password(payload.password),
        telefono=payload.telefono,
        direccion=payload.direccion,
        latitud=payload.latitud,
        longitud=payload.longitud,
        capacidad_max=payload.capacidad_max,
        verificado=payload.verificado,
        activo=True,
        disponible=True,
    )
    db.add(taller)
    db.flush()  # obtener id_taller antes de insertar servicios

    for id_cat in payload.categorias:
        if db.get(CategoriaProblema, id_cat):
            db.add(TallerServicio(
                id_taller=taller.id_taller,
                id_categoria=id_cat,
                servicio_movil=True,
            ))

    db.commit()
    db.refresh(taller)
    return taller


@router.get(
    "/talleres/{id_taller}",
    response_model=TallerAdminStatsResponse,
    summary="Detalle de un taller con estadísticas",
)
def detalle_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    taller = _get_taller_or_404(db, id_taller)

    # Evaluaciones
    eval_row = (
        db.query(
            func.avg(Evaluacion.estrellas).label("promedio"),
            func.count(Evaluacion.id_evaluacion).label("total"),
        )
        .filter(Evaluacion.id_taller == id_taller)
        .first()
    )

    # Servicios completados
    total_servicios = (
        db.query(func.count(Asignacion.id_asignacion))
        .join(EstadoAsignacion, EstadoAsignacion.id_estado_asignacion == Asignacion.id_estado_asignacion)
        .filter(
            Asignacion.id_taller == id_taller,
            EstadoAsignacion.nombre == "completada",
        )
        .scalar()
        or 0
    )

    # Ganancias (solo pagos completados ligados a asignaciones completadas de este taller)
    sub = _subq_asig_completada(db)
    ganancias = (
        db.query(
            func.coalesce(func.sum(Pago.monto_total), 0).label("monto"),
            func.coalesce(func.sum(Pago.comision_plataforma), 0).label("comision"),
        )
        .join(sub, sub.c.id_incidente == Pago.id_incidente)
        .join(EstadoPago, EstadoPago.id_estado_pago == Pago.id_estado_pago)
        .filter(
            sub.c.id_taller == id_taller,
            EstadoPago.nombre == "completado",
        )
        .first()
    )

    promedio = round(float(eval_row.promedio), 2) if eval_row and eval_row.promedio else None

    return TallerAdminStatsResponse(
        **TallerAdminResponse.model_validate(taller).model_dump(),
        promedio_estrellas=promedio,
        total_evaluaciones=eval_row.total if eval_row else 0,
        total_servicios_completados=total_servicios,
        comision_total_generada=float(ganancias.comision) if ganancias else 0.0,
        monto_total_procesado=float(ganancias.monto) if ganancias else 0.0,
    )


@router.patch(
    "/talleres/{id_taller}/verificar",
    response_model=TallerAdminResponse,
    summary="Verificar / desverificar un taller",
)
def toggle_verificar_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    taller = _get_taller_or_404(db, id_taller)
    taller.verificado = not taller.verificado
    db.commit()
    db.refresh(taller)
    return taller


@router.delete(
    "/talleres/{id_taller}",
    summary="Dar de baja un taller (baja lógica)",
    status_code=status.HTTP_200_OK,
)
def eliminar_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    taller = _get_taller_or_404(db, id_taller)
    taller.activo = False
    taller.disponible = False
    db.commit()
    return {"mensaje": f"Taller '{taller.nombre}' dado de baja correctamente"}


# ── GANANCIAS ─────────────────────────────────────────────────────────────────

@router.get(
    "/ganancias/mensual",
    response_model=GananciaMensualResponse,
    summary="Ganancias de la plataforma por mes",
    description=(
        "Retorna la comisión cobrada por la plataforma agrupada por mes. "
        "Filtra opcionalmente por año."
    ),
)
def ganancias_mensuales(
    año: Optional[int] = Query(None, description="Año a consultar (ej. 2025). Sin filtro: todos los años"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = (
        db.query(
            extract("year", Pago.created_at).label("anio"),
            extract("month", Pago.created_at).label("mes"),
            func.count(Pago.id_pago).label("total_pagos"),
            func.coalesce(func.sum(Pago.monto_total), 0).label("monto_total"),
            func.coalesce(func.sum(Pago.comision_plataforma), 0).label("comision"),
        )
        .join(EstadoPago, EstadoPago.id_estado_pago == Pago.id_estado_pago)
        .filter(EstadoPago.nombre == "completado")
    )

    if año:
        q = q.filter(extract("year", Pago.created_at) == año)

    rows = (
        q.group_by(extract("year", Pago.created_at), extract("month", Pago.created_at))
        .order_by(extract("year", Pago.created_at).desc(), extract("month", Pago.created_at).desc())
        .all()
    )

    filas = [
        GananciaMensualRow(
            año=int(r.anio),
            mes=int(r.mes),
            nombre_mes=MONTH_NAMES.get(int(r.mes), ""),
            total_pagos=r.total_pagos,
            monto_total_procesado=round(float(r.monto_total), 2),
            comision_plataforma=round(float(r.comision), 2),
        )
        for r in rows
    ]

    return GananciaMensualResponse(
        filas=filas,
        total_comision=round(sum(f.comision_plataforma for f in filas), 2),
        total_monto_procesado=round(sum(f.monto_total_procesado for f in filas), 2),
    )


@router.get(
    "/ganancias/por-taller",
    response_model=GananciaPorTallerResponse,
    summary="Comisión por taller con rating",
    description=(
        "Retorna la comisión generada por cada taller, ordenada de mayor a menor. "
        "Incluye puntuación promedio. Filtra opcionalmente por año y/o mes."
    ),
)
def ganancias_por_taller(
    año: Optional[int] = Query(None, description="Año (ej. 2025)"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mes (1-12)"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    sub = _subq_asig_completada(db)

    q = (
        db.query(
            Taller.id_taller,
            Taller.nombre,
            Taller.email,
            Taller.verificado,
            Taller.activo,
            func.count(Pago.id_pago).label("total_pagos"),
            func.coalesce(func.sum(Pago.monto_total), 0).label("monto_total"),
            func.coalesce(func.sum(Pago.comision_plataforma), 0).label("comision"),
        )
        .select_from(Taller)
        .join(sub, sub.c.id_taller == Taller.id_taller)
        .join(Pago, Pago.id_incidente == sub.c.id_incidente)
        .join(EstadoPago, EstadoPago.id_estado_pago == Pago.id_estado_pago)
        .filter(EstadoPago.nombre == "completado")
    )

    if año:
        q = q.filter(extract("year", Pago.created_at) == año)
    if mes:
        q = q.filter(extract("month", Pago.created_at) == mes)

    rows = (
        q.group_by(Taller.id_taller, Taller.nombre, Taller.email, Taller.verificado, Taller.activo)
        .order_by(func.sum(Pago.comision_plataforma).desc())
        .all()
    )

    evals = _eval_map(db)

    filas = [
        GananciaTallerRow(
            id_taller=r.id_taller,
            nombre_taller=r.nombre,
            email=r.email,
            verificado=r.verificado,
            activo=r.activo,
            total_pagos=r.total_pagos,
            monto_total=round(float(r.monto_total), 2),
            comision_plataforma=round(float(r.comision), 2),
            promedio_estrellas=round(float(evals[r.id_taller][0]), 2) if r.id_taller in evals and evals[r.id_taller][0] else None,
            total_evaluaciones=evals[r.id_taller][1] if r.id_taller in evals else 0,
        )
        for r in rows
    ]

    return GananciaPorTallerResponse(
        filas=filas,
        total_comision=round(sum(f.comision_plataforma for f in filas), 2),
        total_monto=round(sum(f.monto_total for f in filas), 2),
        filtro_año=año,
        filtro_mes=mes,
    )


# ── NOTIFICACIONES DE PRUEBA ──────────────────────────────────────────────────

@router.post(
    "/usuarios/{id_usuario}/notificacion-prueba",
    summary="Enviar notificación de prueba a un usuario",
    status_code=status.HTTP_200_OK,
)
def enviar_notificacion_prueba(
    id_usuario: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    notif = crear_y_enviar_notificacion(
        db,
        titulo="🔔 Notificación de prueba",
        mensaje="Esta es una notificación de prueba enviada desde el panel de administración.",
        id_usuario=id_usuario,
        push_token=usuario.push_token,
        data={"tipo": "prueba"},
    )
    db.commit()

    return {
        "id_notificacion": notif.id_notificacion,
        "usuario": usuario.nombre,
        "email": usuario.email,
        "push_token": usuario.push_token,
        "enviado_push": notif.enviado_push,
        "mensaje": "Notificación creada en BD" + (" y push enviado" if notif.enviado_push else " (push desactivado: sin credenciales Firebase)"),
    }
