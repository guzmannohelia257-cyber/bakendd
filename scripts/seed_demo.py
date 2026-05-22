"""
Carga datos demo para la defensa.
Idempotente: si ya existen los datos, no falla.

Crea:
  - 3 tenants/talleres con servicios distintos (llantas, mecanica, chaperia)
  - 1 cliente demo con vehiculo
  - 1 tecnico demo vinculado al taller de llantas
  - 1 super-admin

Credenciales: password demo1234 (admin: admin1234)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.catalogos import CategoriaProblema
from app.models.taller import Taller, TallerServicio
from app.models.tenant import Plan, Suscripcion, Tenant
from app.models.usuario import Usuario, Vehiculo
from app.models.usuario_taller import UsuarioTaller


TENANTS = [
    {
        "slug": "demo-llantas",
        "nombre": "Llanteria El Sol",
        "email": "llanteria@demo.com",
        "lat": -16.5000,
        "lng": -68.1500,
        "categorias": ["llantas", "grua_auxilio"],
        "tarifa_traslado": 10,
    },
    {
        "slug": "demo-mecanica",
        "nombre": "Mecanica Central",
        "email": "mecanica@demo.com",
        "lat": -16.5020,
        "lng": -68.1490,
        "categorias": ["mecanica_general", "electrico", "rutinario"],
        "tarifa_traslado": 15,
    },
    {
        "slug": "demo-chaperia",
        "nombre": "Chaperia Express",
        "email": "chaperia@demo.com",
        "lat": -16.4980,
        "lng": -68.1520,
        "categorias": ["chaperia_pintura", "electronico"],
        "tarifa_traslado": 20,
    },
]


def main() -> int:
    db = SessionLocal()
    try:
        plan_free = db.query(Plan).filter_by(codigo="free").one()

        # Tenants + Talleres
        for cfg in TENANTS:
            if db.query(Tenant).filter_by(slug=cfg["slug"]).first():
                print(f"Tenant {cfg['slug']} ya existe, skip")
                continue

            t = Tenant(slug=cfg["slug"], nombre=cfg["nombre"], email_contacto=cfg["email"])
            db.add(t)
            db.flush()
            db.add(Suscripcion(id_tenant=t.id_tenant, id_plan=plan_free.id_plan, estado="activa"))

            taller = Taller(
                id_tenant=t.id_tenant,
                nombre=cfg["nombre"],
                email=cfg["email"],
                password_hash=hash_password("demo1234"),
                latitud=cfg["lat"],
                longitud=cfg["lng"],
                tarifa_traslado=cfg["tarifa_traslado"],
                verificado=True,
                disponible=True,
            )
            db.add(taller)
            db.flush()

            for cod in cfg["categorias"]:
                cat = db.query(CategoriaProblema).filter_by(codigo=cod).first()
                if cat:
                    db.add(
                        TallerServicio(
                            id_taller=taller.id_taller,
                            id_categoria=cat.id_categoria,
                            servicio_movil=True,
                            tarifa_base=100,
                        )
                    )
            print(f"Creado: {cfg['nombre']} ({cfg['slug']})")

        # Cliente demo
        if not db.query(Usuario).filter_by(email="cliente@demo.com").first():
            cliente = Usuario(
                id_rol=1,
                nombre="Cliente Demo",
                email="cliente@demo.com",
                password_hash=hash_password("demo1234"),
                telefono="+591 70000000",
            )
            db.add(cliente)
            db.flush()
            db.add(
                Vehiculo(
                    id_usuario=cliente.id_usuario,
                    placa="DEMO-001",
                    marca="Toyota",
                    modelo="Hilux",
                    anio=2020,
                    color="blanco",
                )
            )
            print("Cliente demo creado")

        # Tecnico demo
        if not db.query(Usuario).filter_by(email="tecnico@demo.com").first():
            tec = Usuario(
                id_rol=3,
                nombre="Tecnico Demo",
                email="tecnico@demo.com",
                password_hash=hash_password("demo1234"),
            )
            db.add(tec)
            db.flush()
            taller_llantas = db.query(Taller).filter_by(email="llanteria@demo.com").first()
            if not taller_llantas:
                raise RuntimeError("No se encontro el taller demo de llantas")
            db.add(
                UsuarioTaller(
                    id_usuario=tec.id_usuario,
                    id_taller=taller_llantas.id_taller,
                    activo=True,
                )
            )
            print("Tecnico demo creado")

        # Super-admin
        if not db.query(Usuario).filter_by(email="admin@demo.com").first():
            adm = Usuario(
                id_rol=4,
                nombre="Super Admin",
                email="admin@demo.com",
                password_hash=hash_password("admin1234"),
            )
            db.add(adm)
            print("Super-admin creado")

        db.commit()
        print("\nLISTO. Credenciales con password: demo1234 (admin: admin1234)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
