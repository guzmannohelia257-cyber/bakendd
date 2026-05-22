"""
Calculo de KPIs por tenant.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.models.catalogos import CategoriaProblema, EstadoAsignacion
from app.models.incidente import (
    Asignacion,
    Evaluacion,
    HistorialEstadoAsignacion,
    Incidente,
    CandidatoAsignacion,
)
from app.models.taller import Taller


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


def resumen_completo(
    db: Session,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    id_tenant: Optional[int] = None,
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
    }
