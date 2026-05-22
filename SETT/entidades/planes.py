"""Planes del SaaS (Free, Pro, Enterprise)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tenant import Plan
from SETT.config import PLANES
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    for p in PLANES:
        plan = Plan(
            codigo=p["codigo"],
            nombre=p["nombre"],
            descripcion=p["descripcion"],
            precio_mensual=p["precio_mensual"],
            max_talleres=p["max_talleres"],
            max_tecnicos=p["max_tecnicos"],
            max_incidentes_mes=p["max_incidentes_mes"],
            feature_websockets=p["feature_websockets"],
            feature_kpis_avanzados=p["feature_kpis_avanzados"],
            feature_reportes_ia=p["feature_reportes_ia"],
            activo=True,
        )
        db.add(plan)
    db.commit()

    for p in db.query(Plan).all():
        ctx.plan[p.codigo] = p

    logger.info(f"[entidades] {len(ctx.plan)} planes (free/pro/enterprise)")
