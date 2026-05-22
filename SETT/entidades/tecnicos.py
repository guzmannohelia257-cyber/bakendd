"""
Tecnicos: usuarios con rol=tecnico vinculados a un taller via usuario_taller.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.usuario import Usuario
from app.models.usuario_taller import UsuarioTaller
from SETT.config import TECNICOS
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    rol_tecnico = ctx.rol["tecnico"]

    for t in TECNICOS:
        usuario = Usuario(
            id_rol=rol_tecnico.id_rol,
            nombre=t["nombre"],
            email=t["email"],
            telefono=t["telefono"],
            password_hash=hash_password(t["password"]),
            activo=True,
        )
        db.add(usuario)
        db.flush()

        taller = ctx.talleres[t["taller_idx"]]
        db.add(UsuarioTaller(
            id_usuario=usuario.id_usuario,
            id_taller=taller.id_taller,
            disponible=True,
            activo=True,
            latitud=taller.latitud,
            longitud=taller.longitud,
        ))

        ctx.tecnicos.append(usuario)

    db.commit()
    for u in ctx.tecnicos:
        db.refresh(u)

    logger.info(f"[entidades] {len(ctx.tecnicos)} tecnicos vinculados a talleres")
