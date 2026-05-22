"""
Escenario 01 — incidente recien reportado, sin taller activo aun.
  estado_incidente  = pendiente
  estado_asignacion = pendiente
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_pendiente",
        taller_idx=0,
        descripcion="Mi bateria esta descargada, no enciende el auto.",
        categoria="bateria",
        prioridad="media",
        estado_incidente="pendiente",
        estado_asignacion="pendiente",
        lat=-17.802625, lng=-63.200045,
    ))
