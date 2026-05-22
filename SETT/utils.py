"""
Helpers compartidos por todos los modulos del SETT.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import Base, engine

logger = logging.getLogger("SETT")


class Ctx:
    """
    Contexto compartido entre catalogos / entidades / escenarios.

    Cada seeder agrega aqui las entidades que crea para que los siguientes
    pasos las usen sin re-consultarlas.
    """

    def __init__(self) -> None:
        # catalogos por nombre
        self.rol: dict[str, Any] = {}
        self.estado_incidente: dict[str, Any] = {}
        self.estado_asignacion: dict[str, Any] = {}
        self.estado_pago: dict[str, Any] = {}
        self.estado_cotizacion: dict[str, Any] = {}
        self.categoria: dict[str, Any] = {}
        self.prioridad: dict[str, Any] = {}
        self.tipo_evidencia: dict[str, Any] = {}
        self.metodo_pago: dict[str, Any] = {}
        self.plan: dict[str, Any] = {}
        # entidades
        self.admin: Any = None
        self.talleres: list[Any] = []
        self.tecnicos: list[Any] = []
        self.clientes: dict[str, Any] = {}        # key -> Usuario
        self.vehiculos: dict[str, Any] = {}       # key cliente -> Vehiculo
        # contador de escenarios
        self.escenarios_creados: int = 0


def ensure_tables() -> None:
    """Crea las tablas si no existen (primer arranque sobre BD vacia)."""
    Base.metadata.create_all(bind=engine)
    logger.info("[SETT] Tablas verificadas / creadas")


def truncate_all(db: Session, tablas: list[str]) -> None:
    """
    TRUNCATE CASCADE sobre todas las tablas listadas, reiniciando secuencias.

    Cada TRUNCATE va en su propia transaccion para que si una tabla no existe
    en una BD parcialmente migrada no aborte la limpieza completa.
    """
    for t in tablas:
        try:
            db.execute(text(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE;'))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.info(f"[SETT] (skip) {t}: {e}")
    logger.info(f"[SETT] {len(tablas)} tablas truncadas")


def resumen(db: Session) -> None:
    """Imprime conteo final y credenciales utiles."""
    from SETT.config import ADMIN, CLIENTES, TALLERES, TECNICOS

    tablas = [
        "rol", "estado_incidente", "estado_asignacion", "estado_cotizacion",
        "estado_pago", "categoria_problema", "prioridad", "tipo_evidencia",
        "metodo_pago", "plan", "tenant", "suscripcion",
        "usuario", "taller", "taller_servicio", "usuario_taller", "vehiculo",
        "incidente", "asignacion", "candidato_asignacion",
        "historial_estado_incidente", "historial_estado_asignacion",
        "cotizacion", "evidencia", "mensaje", "notificacion",
        "metrica", "pago", "evaluacion",
    ]

    print("\n" + "=" * 72)
    print(" RESUMEN SETT ".center(72, "="))
    print("=" * 72)
    for t in tablas:
        try:
            n = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:32s} {n}")
        except Exception:
            pass

    print("\n" + "-" * 72)
    print(" CREDENCIALES DE LOGIN ".center(72, "-"))
    print("-" * 72)
    print(f"  ADMIN   : {ADMIN['email']:38s}  pwd: {ADMIN['password']}")
    print()
    for t in TALLERES:
        print(f"  TALLER  : {t['email']:38s}  pwd: {t['password']}")
    print()
    for t in TECNICOS:
        print(f"  TECNICO : {t['email']:38s}  pwd: {t['password']}")
    print()
    for c in CLIENTES:
        print(f"  CLIENTE : {c['email']:38s}  pwd: {c['password']}  ({c['key']})")
    print("=" * 72 + "\n")
