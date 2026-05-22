"""
Escenario 08 — cotizacion creada pero el taller aun no le pone monto.
  estado_incidente  = pendiente
  estado_asignacion = pendiente
  cotizacion        = pendiente
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_cot_pendiente",
        taller_idx=1,
        descripcion="Ruido extranio del motor, necesito diagnostico.",
        categoria="Mecanica general",
        prioridad="media",
        estado_incidente="pendiente",
        estado_asignacion="pendiente",
        lat=-17.793800, lng=-63.192100,
        cotizacion_estado="pendiente",
        cotizacion_monto=150.00,
    ))
