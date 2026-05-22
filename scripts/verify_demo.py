"""Verifica que los datos demo existen y son consistentes."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.taller import Taller
from app.models.tenant import Tenant
from app.models.usuario import Usuario


def main() -> int:
    db = SessionLocal()
    checks: list[tuple[str, bool, str]] = []

    n_tenants = db.query(Tenant).filter(Tenant.slug.like("demo-%")).count()
    checks.append(("3 tenants demo", n_tenants == 3, f"hay {n_tenants}"))

    n_talleres = db.query(Taller).join(Tenant).filter(Tenant.slug.like("demo-%")).count()
    checks.append(("3 talleres demo", n_talleres == 3, f"hay {n_talleres}"))

    cliente = db.query(Usuario).filter_by(email="cliente@demo.com").first()
    checks.append(("cliente demo", cliente is not None, "no existe" if not cliente else "OK"))

    tec = db.query(Usuario).filter_by(email="tecnico@demo.com").first()
    checks.append(("tecnico demo", tec is not None and tec.id_rol == 3, "no existe o rol incorrecto"))

    admin = db.query(Usuario).filter_by(email="admin@demo.com").first()
    checks.append(("super-admin", admin is not None and admin.id_rol == 4, "no existe o rol incorrecto"))

    print("\n== Verificacion datos demo ==")
    ok = True
    for nombre, passed, detail in checks:
        icon = "OK" if passed else "FALLO"
        print(f"  [{icon}] {nombre} -- {detail}")
        if not passed:
            ok = False

    db.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
