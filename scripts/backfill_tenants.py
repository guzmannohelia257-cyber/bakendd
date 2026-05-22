"""
Backfill 1 taller = 1 tenant.

Para cada Taller con id_tenant=NULL:
  1. Crea un Tenant (slug derivado del email del taller, nombre = nombre del taller).
  2. Crea una Suscripcion al plan 'free' por defecto.
  3. Asigna taller.id_tenant <- nuevo tenant.

Para cada tabla transaccional tenant-scoped (incidente, asignacion, evidencia,
evaluacion, mensaje, notificacion, pago, metrica), backfilea id_tenant desde
el id_taller relacionado.

Idempotente: si ya hay id_tenant, lo respeta. Se puede correr multiples veces.

Uso:
    python -m scripts.backfill_tenants                 # ejecuta
    python -m scripts.backfill_tenants --dry-run       # solo reporta
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
import app.models  # noqa: F401  registra tablas
from app.models.taller import Taller
from app.models.tenant import Plan, Tenant, Suscripcion


# Tablas transaccionales que tienen id_tenant Y se pueden derivar via id_taller
# (directa o indirectamente a traves de incidente -> asignacion -> id_taller).
# (tabla, query_de_backfill) donde la query setea id_tenant donde sea NULL.
BACKFILL_QUERIES: list[tuple[str, str]] = [
    # Asignacion: directo via id_taller
    ("asignacion", """
        UPDATE asignacion a
        SET id_tenant = t.id_tenant
        FROM taller t
        WHERE a.id_taller = t.id_taller
          AND a.id_tenant IS NULL
          AND t.id_tenant IS NOT NULL
    """),
    # Incidente: heredado de la asignacion (1er taller asignado)
    ("incidente", """
        UPDATE incidente i
        SET id_tenant = sub.id_tenant
        FROM (
            SELECT DISTINCT ON (id_incidente) id_incidente, id_tenant
            FROM asignacion
            WHERE id_tenant IS NOT NULL
            ORDER BY id_incidente, created_at ASC
        ) sub
        WHERE i.id_incidente = sub.id_incidente
          AND i.id_tenant IS NULL
    """),
    # Evidencia: heredado del incidente
    ("evidencia", """
        UPDATE evidencia e
        SET id_tenant = i.id_tenant
        FROM incidente i
        WHERE e.id_incidente = i.id_incidente
          AND e.id_tenant IS NULL
          AND i.id_tenant IS NOT NULL
    """),
    # Evaluacion: directo via id_taller
    ("evaluacion", """
        UPDATE evaluacion ev
        SET id_tenant = t.id_tenant
        FROM taller t
        WHERE ev.id_taller = t.id_taller
          AND ev.id_tenant IS NULL
          AND t.id_tenant IS NOT NULL
    """),
    # Mensaje: heredado del incidente
    ("mensaje", """
        UPDATE mensaje m
        SET id_tenant = i.id_tenant
        FROM incidente i
        WHERE m.id_incidente = i.id_incidente
          AND m.id_tenant IS NULL
          AND i.id_tenant IS NOT NULL
    """),
    # Notificacion: heredado del incidente o del taller
    ("notificacion_via_incidente", """
        UPDATE notificacion n
        SET id_tenant = i.id_tenant
        FROM incidente i
        WHERE n.id_incidente = i.id_incidente
          AND n.id_tenant IS NULL
          AND i.id_tenant IS NOT NULL
    """),
    ("notificacion_via_taller", """
        UPDATE notificacion n
        SET id_tenant = t.id_tenant
        FROM taller t
        WHERE n.id_taller = t.id_taller
          AND n.id_tenant IS NULL
          AND t.id_tenant IS NOT NULL
    """),
    # Pago: heredado del incidente
    ("pago", """
        UPDATE pago p
        SET id_tenant = i.id_tenant
        FROM incidente i
        WHERE p.id_incidente = i.id_incidente
          AND p.id_tenant IS NULL
          AND i.id_tenant IS NOT NULL
    """),
    # Metrica: heredado del incidente
    ("metrica", """
        UPDATE metrica m
        SET id_tenant = i.id_tenant
        FROM incidente i
        WHERE m.id_incidente = i.id_incidente
          AND m.id_tenant IS NULL
          AND i.id_tenant IS NOT NULL
    """),
]


def _slugify(value: str) -> str:
    """Convierte un texto a slug (a-z0-9-)."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "tenant"


def _unique_slug(db: Session, base: str) -> str:
    """Garantiza unicidad anadiendo sufijo numerico si hace falta."""
    slug = base[:45] if len(base) > 45 else base
    if not db.query(Tenant).filter(Tenant.slug == slug).first():
        return slug
    i = 2
    while True:
        candidate = f"{slug}-{i}"[:50]
        if not db.query(Tenant).filter(Tenant.slug == candidate).first():
            return candidate
        i += 1


def backfill(dry_run: bool = False) -> int:
    db: Session = SessionLocal()
    try:
        plan_free = db.query(Plan).filter(Plan.codigo == "free").first()
        if plan_free is None:
            print("ERROR: no existe plan 'free'. Corre la migracion 0002 primero.")
            return 1

        talleres_sin_tenant = db.query(Taller).filter(Taller.id_tenant.is_(None)).all()
        print(f"[1/2] Talleres sin tenant: {len(talleres_sin_tenant)}")

        created = 0
        for taller in talleres_sin_tenant:
            base_slug = _slugify(taller.email.split("@")[0] if taller.email else taller.nombre)
            slug = _unique_slug(db, base_slug)

            tenant = Tenant(
                slug=slug,
                nombre=taller.nombre,
                email_contacto=taller.email,
                telefono=taller.telefono,
            )
            db.add(tenant)
            db.flush()  # obtener id_tenant

            sub = Suscripcion(
                id_tenant=tenant.id_tenant,
                id_plan=plan_free.id_plan,
                estado="activa",
            )
            db.add(sub)

            taller.id_tenant = tenant.id_tenant
            created += 1
            print(f"  taller={taller.id_taller} '{taller.nombre}' -> tenant slug='{slug}'")

        if dry_run:
            print("[DRY-RUN] no se commitea")
            db.rollback()
            return 0

        db.commit()
        print(f"[1/2] Tenants creados: {created}")

        # Propagar id_tenant en transaccionales
        print("[2/2] Backfill de tablas transaccionales:")
        for nombre, sql in BACKFILL_QUERIES:
            result = db.execute(text(sql))
            print(f"  {nombre}: {result.rowcount} filas actualizadas")
        db.commit()
        print("OK")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc!r}")
        return 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
