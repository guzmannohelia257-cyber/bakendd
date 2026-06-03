"""
Calculo de KPIs por tenant.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Integer, cast, desc, func, select
from sqlalchemy.orm import Session

from app.models.catalogos import CategoriaProblema, EstadoAsignacion, EstadoIncidente
from app.models.incidente import (
    Asignacion,
    Evaluacion,
    HistorialEstadoAsignacion,
    Incidente,
    CandidatoAsignacion,
)
from app.models.taller import Taller


SLA_MINUTOS_DEFAULT = 60


def _rango_default():
    """Default: ultimos 30 dias hasta hoy."""
    hasta = datetime.now(timezone.utc)
    desde = hasta - timedelta(days=30)
    return desde, hasta


def tiempo_promedio_asignacion_min(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
) -> float:
    """
    Promedio en minutos desde que el cliente crea el incidente
    hasta que se crea la primera asignacion aceptada.
    """
    estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    if not estado_aceptada:
        return 0.0

    q = (
        select(
            func.avg(func.extract("epoch", Asignacion.created_at - Incidente.created_at) / 60)
        )
        .select_from(Asignacion)
        .join(Incidente, Incidente.id_incidente == Asignacion.id_incidente)
        .where(Asignacion.created_at.between(desde, hasta))
        .where(Asignacion.id_estado_asignacion == estado_aceptada.id_estado_asignacion)
    )
    if id_tenant is not None:
        q = q.where(Asignacion.id_tenant == id_tenant)

    val = db.execute(q).scalar()
    return float(val or 0)


def tiempo_promedio_llegada_min(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
) -> float:
    """
    Promedio en minutos entre transicion 'aceptada' -> 'llegado',
    leido de historial_estado_asignacion.
    """
    estado_llegado = db.query(EstadoAsignacion).filter_by(nombre="llegado").first()
    estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    if not (estado_llegado and estado_aceptada):
        return 0.0

    sub_acept = (
        select(
            HistorialEstadoAsignacion.id_asignacion.label("aid"),
            func.min(HistorialEstadoAsignacion.created_at).label("ts_aceptada"),
        )
        .where(HistorialEstadoAsignacion.id_estado_nuevo == estado_aceptada.id_estado_asignacion)
        .group_by(HistorialEstadoAsignacion.id_asignacion)
        .subquery()
    )

    sub_llego = (
        select(
            HistorialEstadoAsignacion.id_asignacion.label("aid"),
            func.min(HistorialEstadoAsignacion.created_at).label("ts_llego"),
        )
        .where(HistorialEstadoAsignacion.id_estado_nuevo == estado_llegado.id_estado_asignacion)
        .group_by(HistorialEstadoAsignacion.id_asignacion)
        .subquery()
    )

    q = (
        select(
            func.avg(func.extract("epoch", sub_llego.c.ts_llego - sub_acept.c.ts_aceptada) / 60)
        )
        .select_from(sub_acept)
        .join(sub_llego, sub_llego.c.aid == sub_acept.c.aid)
        .join(Asignacion, Asignacion.id_asignacion == sub_acept.c.aid)
        .where(sub_llego.c.ts_llego.between(desde, hasta))
    )
    if id_tenant is not None:
        q = q.where(Asignacion.id_tenant == id_tenant)

    val = db.execute(q).scalar()
    return float(val or 0)


def incidentes_por_categoria(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
) -> list[dict]:
    q = (
        select(
            CategoriaProblema.codigo,
            CategoriaProblema.nombre,
            func.count(Incidente.id_incidente).label("total"),
        )
        .select_from(Incidente)
        .join(CategoriaProblema, CategoriaProblema.id_categoria == Incidente.id_categoria)
        .where(Incidente.created_at.between(desde, hasta))
        .group_by(CategoriaProblema.codigo, CategoriaProblema.nombre)
        .order_by(func.count(Incidente.id_incidente).desc())
    )
    if id_tenant is not None:
        q = q.where(Incidente.id_tenant == id_tenant)

    return [
        {"codigo": r.codigo, "nombre": r.nombre, "total": int(r.total)}
        for r in db.execute(q).all()
    ]


def ranking_talleres(db: Session, desde: datetime, hasta: datetime, limite: int = 10) -> list[dict]:
    """
    Ranking GLOBAL por tenant (super-admin). Para listar talleres dentro de
    un tenant especifico, agregar where Taller.id_tenant=....
    """
    estado_completada = db.query(EstadoAsignacion).filter_by(nombre="completada").first()

    sub_rating = (
        select(
            Evaluacion.id_taller,
            func.avg(Evaluacion.estrellas).label("rating"),
            func.count(Evaluacion.id_evaluacion).label("n_eval"),
        )
        .where(Evaluacion.created_at.between(desde, hasta))
        .group_by(Evaluacion.id_taller)
        .subquery()
    )

    sub_completadas = (
        select(
            Asignacion.id_taller,
            func.count(Asignacion.id_asignacion).label("n_completadas"),
        )
        .where(
            Asignacion.id_estado_asignacion
            == (estado_completada.id_estado_asignacion if estado_completada else -1),
            Asignacion.updated_at.between(desde, hasta),
        )
        .group_by(Asignacion.id_taller)
        .subquery()
    )

    sub_candidatos = (
        select(
            CandidatoAsignacion.id_taller,
            func.count(CandidatoAsignacion.id_candidato).label("n_cand"),
            func.sum(cast(CandidatoAsignacion.seleccionado, Integer)).label("n_acept"),
        )
        .group_by(CandidatoAsignacion.id_taller)
        .subquery()
    )

    q = (
        select(
            Taller.id_taller,
            Taller.nombre,
            sub_rating.c.rating,
            sub_completadas.c.n_completadas,
            sub_candidatos.c.n_cand,
            sub_candidatos.c.n_acept,
        )
        .select_from(Taller)
        .outerjoin(sub_rating, sub_rating.c.id_taller == Taller.id_taller)
        .outerjoin(sub_completadas, sub_completadas.c.id_taller == Taller.id_taller)
        .outerjoin(sub_candidatos, sub_candidatos.c.id_taller == Taller.id_taller)
        .where(Taller.activo.is_(True))
    )

    filas = db.execute(q).all()

    import math

    resultado = []
    for r in filas:
        rating = float(r.rating or 0)
        n_cand = int(r.n_cand or 0)
        n_acept = int(r.n_acept or 0)
        tasa = (n_acept / n_cand) if n_cand else 0
        n_comp = int(r.n_completadas or 0)
        score = (rating / 5.0) * 0.5 + tasa * 0.3 + min(math.log(n_comp + 1) / 5, 1) * 0.2

        resultado.append(
            {
                "id_taller": r.id_taller,
                "nombre": r.nombre,
                "rating_promedio": round(rating, 2),
                "completadas": n_comp,
                "tasa_aceptacion": round(tasa, 2),
                "score": round(score, 3),
            }
        )

    resultado.sort(key=lambda x: x["score"], reverse=True)
    return resultado[:limite]


def incidentes_cancelados(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
) -> int:
    """
    Cantidad de incidentes con estado 'cancelado' creados en el rango.
    """
    estado_cancelado = db.query(EstadoIncidente).filter_by(nombre="cancelado").first()
    if not estado_cancelado:
        return 0

    q = (
        select(func.count(Incidente.id_incidente))
        .where(Incidente.id_estado == estado_cancelado.id_estado)
        .where(Incidente.created_at.between(desde, hasta))
    )
    if id_tenant is not None:
        q = q.where(Incidente.id_tenant == id_tenant)

    val = db.execute(q).scalar()
    return int(val or 0)


def zonas_mas_incidentes(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
    limite: int = 10,
    precision_decimales: int = 2,
) -> list[dict]:
    """
    Agrupa incidentes por zona geografica aproximada (redondeo de lat/lng).
    Default 2 decimales = celdas de ~1 km^2.
    """
    lat_round = func.round(cast(Incidente.latitud, sa_numeric()), precision_decimales)
    lng_round = func.round(cast(Incidente.longitud, sa_numeric()), precision_decimales)

    q = (
        select(
            lat_round.label("lat"),
            lng_round.label("lng"),
            func.count(Incidente.id_incidente).label("total"),
        )
        .where(Incidente.created_at.between(desde, hasta))
        .group_by("lat", "lng")
        .order_by(desc("total"))
        .limit(limite)
    )
    if id_tenant is not None:
        q = q.where(Incidente.id_tenant == id_tenant)

    return [
        {"lat": float(r.lat), "lng": float(r.lng), "total": int(r.total)}
        for r in db.execute(q).all()
    ]


def cumplimiento_sla(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
    sla_minutos: int = SLA_MINUTOS_DEFAULT,
) -> dict:
    """
    Porcentaje de asignaciones completadas dentro del umbral SLA
    (tiempo desde creacion del incidente hasta marca 'completada' en historial).
    Retorna {'total_completadas': int, 'cumplen_sla': int, 'porcentaje': float, 'sla_minutos': int}.
    """
    estado_completada = db.query(EstadoAsignacion).filter_by(nombre="completada").first()
    if not estado_completada:
        return {
            "total_completadas": 0,
            "cumplen_sla": 0,
            "porcentaje": 0.0,
            "sla_minutos": sla_minutos,
        }

    sub_completada = (
        select(
            HistorialEstadoAsignacion.id_asignacion.label("aid"),
            func.min(HistorialEstadoAsignacion.created_at).label("ts_fin"),
        )
        .where(
            HistorialEstadoAsignacion.id_estado_nuevo
            == estado_completada.id_estado_asignacion
        )
        .group_by(HistorialEstadoAsignacion.id_asignacion)
        .subquery()
    )

    base = (
        select(
            Asignacion.id_asignacion,
            (
                func.extract("epoch", sub_completada.c.ts_fin - Incidente.created_at) / 60
            ).label("duracion_min"),
        )
        .select_from(Asignacion)
        .join(sub_completada, sub_completada.c.aid == Asignacion.id_asignacion)
        .join(Incidente, Incidente.id_incidente == Asignacion.id_incidente)
        .where(sub_completada.c.ts_fin.between(desde, hasta))
    )
    if id_tenant is not None:
        base = base.where(Asignacion.id_tenant == id_tenant)

    base_sub = base.subquery()
    total = db.execute(
        select(func.count()).select_from(base_sub)
    ).scalar() or 0
    cumplen = db.execute(
        select(func.count())
        .select_from(base_sub)
        .where(base_sub.c.duracion_min <= sla_minutos)
    ).scalar() or 0

    porcentaje = (float(cumplen) / float(total) * 100.0) if total else 0.0
    return {
        "total_completadas": int(total),
        "cumplen_sla": int(cumplen),
        "porcentaje": round(porcentaje, 2),
        "sla_minutos": sla_minutos,
    }


def sa_numeric():
    """Lazy import para no romper si SQLAlchemy types se reorganizan."""
    from sqlalchemy import Numeric

    return Numeric(10, 6)


def total_incidentes(
    db: Session,
    desde: datetime,
    hasta: datetime,
    id_tenant: Optional[int] = None,
) -> int:
    """Cantidad de incidentes creados en el rango (para tarjetas/comparativa)."""
    q = select(func.count(Incidente.id_incidente)).where(
        Incidente.created_at.between(desde, hasta)
    )
    if id_tenant is not None:
        q = q.where(Incidente.id_tenant == id_tenant)
    return int(db.execute(q).scalar() or 0)


def resumen_completo(
    db: Session,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    id_tenant: Optional[int] = None,
    sla_minutos: int = SLA_MINUTOS_DEFAULT,
) -> dict:
    if desde is None or hasta is None:
        desde, hasta = _rango_default()
    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "tiempo_promedio_asignacion_min": round(
            tiempo_promedio_asignacion_min(db, desde, hasta, id_tenant), 2
        ),
        "tiempo_promedio_llegada_min": round(
            tiempo_promedio_llegada_min(db, desde, hasta, id_tenant), 2
        ),
        "incidentes_por_categoria": incidentes_por_categoria(db, desde, hasta, id_tenant),
        "casos_cancelados": incidentes_cancelados(db, desde, hasta, id_tenant),
        "total_incidentes": total_incidentes(db, desde, hasta, id_tenant),
        "zonas_mas_incidentes": zonas_mas_incidentes(db, desde, hasta, id_tenant),
        "sla_cumplimiento": cumplimiento_sla(db, desde, hasta, id_tenant, sla_minutos),
    }


def kpis_por_taller(
    db: Session,
    desde: datetime,
    hasta: datetime,
    sla_minutos: int = SLA_MINUTOS_DEFAULT,
) -> list[dict]:
    """KPIs escalares por cada taller activo, para la comparativa del super-admin.

    Recorre los talleres y reutiliza las mismas funciones por tenant. Debe
    invocarse con el filtro global de tenant desactivado (current_tenant.set(0)).
    """
    talleres = (
        db.query(Taller).filter(Taller.activo.is_(True)).order_by(Taller.nombre).all()
    )
    filas: list[dict] = []
    for t in talleres:
        tid = t.id_tenant
        sla = cumplimiento_sla(db, desde, hasta, tid, sla_minutos)
        filas.append(
            {
                "id_taller": t.id_taller,
                "id_tenant": tid,
                "nombre": t.nombre,
                "tiempo_asignacion_min": round(
                    tiempo_promedio_asignacion_min(db, desde, hasta, tid), 2
                ),
                "tiempo_llegada_min": round(
                    tiempo_promedio_llegada_min(db, desde, hasta, tid), 2
                ),
                "total_incidentes": total_incidentes(db, desde, hasta, tid),
                "casos_cancelados": incidentes_cancelados(db, desde, hasta, tid),
                "sla_porcentaje": sla["porcentaje"],
                "completadas": sla["total_completadas"],
            }
        )
    return filas
