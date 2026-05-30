#!/usr/bin/env python3
"""
Bootstrap de base de datos para el arranque (Render / local).

Problema que resuelve
---------------------
La migracion 0001 es un baseline VACIO: asume que las tablas base (usuario,
taller, etc.) ya existen porque historicamente se crearon con
`Base.metadata.create_all`. Por eso, sobre una BD COMPLETAMENTE NUEVA,
`alembic upgrade head` revienta en la 0002 al crear `tenant_user` con
FK a `usuario` (que todavia no existe):

    psycopg2.errors.UndefinedTable: relation "usuario" does not exist

Logica
------
- BD vacia (no existe tabla `usuario`)      -> create_all() + alembic stamp head
- BD con tablas pero sin alembic_version    -> alembic stamp head
- BD ya inicializada (existe `usuario`)      -> alembic upgrade head (migra pendientes)

Es idempotente y seguro de correr en cada deploy.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permitir imports `app.*` y encontrar alembic.ini desde la raiz del backend
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import inspect  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
import app.models  # noqa: F401,E402  -> registra todas las tablas en Base.metadata


def main() -> int:
    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))

    inspector = inspect(engine)
    tablas = set(inspector.get_table_names())
    tiene_usuario = "usuario" in tablas
    tiene_alembic = "alembic_version" in tablas

    if not tiene_usuario:
        print("[bootstrap] BD vacia -> create_all() + stamp head")
        Base.metadata.create_all(bind=engine)
        command.stamp(alembic_cfg, "head")
    elif not tiene_alembic:
        print("[bootstrap] BD con tablas sin alembic_version -> stamp head")
        command.stamp(alembic_cfg, "head")
    else:
        print("[bootstrap] BD existente -> alembic upgrade head")
        command.upgrade(alembic_cfg, "head")

    print("[bootstrap] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
