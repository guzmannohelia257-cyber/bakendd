"""
Escenario 09 — el taller envio cotizacion, el cliente debe decidir.
  estado_incidente  = pendiente
  estado_asignacion = pendiente
  cotizacion        = enviada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_cot_enviada",
        taller_idx=1,
        descripcion="No prenden las luces ni el tablero.",
        categoria="Servicio electrico",
        prioridad="alta",
        estado_incidente="pendiente",
        estado_asignacion="pendiente",
        lat=-17.811200, lng=-63.179600,
        cotizacion_estado="enviada",
        cotizacion_monto=200.00,
    ))
