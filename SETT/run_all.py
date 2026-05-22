"""
Orquestador principal del SETT.

Pasos:
  1. Asegura el schema (create_all)
  2. TRUNCATE CASCADE de todas las tablas operativas
  3. Cataloga (roles, estados, categorias, prioridades, tipos_evidencia, metodos_pago)
  4. Entidades (planes, tenants+talleres, admin, tecnicos, clientes)
  5. Escenarios 01..15 (uno por combinacion de estados a cubrir)
  6. Resumen + credenciales

Uso:
    python -m SETT.run_all

En despliegue (Render):
    bash despliegue/start.sh   # invoca este modulo si SEED_ON_STARTUP=true
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Permitir ejecucion como script suelto (python SETT/run_all.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
import app.models  # noqa: F401,E402  registra todas las tablas

from SETT.catalogos import categorias as cat_categorias  # noqa: E402
from SETT.catalogos import estados as cat_estados  # noqa: E402
from SETT.catalogos import roles as cat_roles  # noqa: E402
from SETT.config import TABLAS_A_LIMPIAR  # noqa: E402
from SETT.entidades import admin as ent_admin  # noqa: E402
from SETT.entidades import clientes as ent_clientes  # noqa: E402
from SETT.entidades import planes as ent_planes  # noqa: E402
from SETT.entidades import talleres as ent_talleres  # noqa: E402
from SETT.entidades import tecnicos as ent_tecnicos  # noqa: E402
from SETT.escenarios import (  # noqa: E402
    e01_pendiente, e02_aceptada, e03_rechazada, e04_en_camino,
    e05_llegado, e06_atendido, e07_cancelado,
    e08_cot_pendiente, e09_cot_enviada, e10_cot_aceptada,
    e11_cot_rechazada, e12_cot_expirada,
    e13_pago_procesando, e14_pago_fallido, e15_pago_reembolsado,
    e16_pago_pendiente,
)
from SETT.utils import Ctx, ensure_tables, logger, resumen, truncate_all  # noqa: E402


# Orden FIJO de los escenarios. No mover sin saber por que.
ESCENARIOS = [
    e01_pendiente,
    e02_aceptada,
    e03_rechazada,
    e04_en_camino,
    e05_llegado,
    e06_atendido,
    e07_cancelado,
    e08_cot_pendiente,
    e09_cot_enviada,
    e10_cot_aceptada,
    e11_cot_rechazada,
    e12_cot_expirada,
    e13_pago_procesando,
    e14_pago_fallido,
    e15_pago_reembolsado,
    e16_pago_pendiente,
]


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from app.core.config import get_settings
    host = get_settings().DATABASE_URL.split("@")[-1]
    logger.info(f"[SETT] DATABASE host: {host}")

    ensure_tables()

    db = SessionLocal()
    ctx = Ctx()
    try:
        truncate_all(db, TABLAS_A_LIMPIAR)

        # ── Catalogos ──────────────────────────────────────────────
        cat_roles.run(db, ctx)
        cat_estados.run(db, ctx)
        cat_categorias.run(db, ctx)

        # ── Entidades ──────────────────────────────────────────────
        ent_planes.run(db, ctx)
        ent_admin.run(db, ctx)
        ent_talleres.run(db, ctx)
        ent_tecnicos.run(db, ctx)
        ent_clientes.run(db, ctx)

        # ── Escenarios ─────────────────────────────────────────────
        for modulo in ESCENARIOS:
            modulo.run(db, ctx)

        resumen(db)
        logger.info(
            f"[SETT] OK — base poblada con {ctx.escenarios_creados} escenarios"
        )
    except Exception:
        db.rollback()
        logger.exception("[SETT] FALLO")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
