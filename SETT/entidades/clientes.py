"""
Clientes + vehiculos. Uno por escenario para mantener cada flujo aislado.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.usuario import Usuario, Vehiculo
from SETT.config import CLIENTES
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    rol_cliente = ctx.rol["cliente"]

    for c in CLIENTES:
        cliente = Usuario(
            id_rol=rol_cliente.id_rol,
            nombre=c["nombre"],
            email=c["email"],
            telefono=c["telefono"],
            password_hash=hash_password(c["password"]),
            activo=True,
        )
        db.add(cliente)
        db.flush()

        v = c["vehiculo"]
        vehiculo = Vehiculo(
            id_usuario=cliente.id_usuario,
            placa=v["placa"],
            marca=v["marca"],
            modelo=v["modelo"],
            anio=v["anio"],
            color=v["color"],
            activo=True,
        )
        db.add(vehiculo)
        db.flush()

        ctx.clientes[c["key"]] = cliente
        ctx.vehiculos[c["key"]] = vehiculo

    db.commit()
    for c in ctx.clientes.values():
        db.refresh(c)
    for v in ctx.vehiculos.values():
        db.refresh(v)

    logger.info(f"[entidades] {len(ctx.clientes)} clientes + vehiculos")
