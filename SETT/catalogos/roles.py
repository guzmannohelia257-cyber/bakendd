"""Roles del sistema: cliente, taller, tecnico, admin."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.catalogos import Rol
from SETT.config import ROLES
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    for nombre in ROLES:
        r = Rol(nombre=nombre)
        db.add(r)
    db.commit()

    for r in db.query(Rol).all():
        ctx.rol[r.nombre] = r

    logger.info(f"[catalogos] {len(ctx.rol)} roles")
