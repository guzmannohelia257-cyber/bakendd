"""Admin del sistema (rol=admin)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.usuario import Usuario
from SETT.config import ADMIN
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    rol_admin = ctx.rol["admin"]
    admin = Usuario(
        id_rol=rol_admin.id_rol,
        nombre=ADMIN["nombre"],
        email=ADMIN["email"],
        telefono=ADMIN["telefono"],
        password_hash=hash_password(ADMIN["password"]),
        activo=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    ctx.admin = admin

    logger.info(f"[entidades] admin: {admin.email}")
