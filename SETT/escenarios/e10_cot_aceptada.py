"""
Escenario 10 — cliente acepto cotizacion, el servicio esta en curso.
  estado_incidente  = en_proceso
  estado_asignacion = en_camino
  cotizacion        = aceptada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_cot_aceptada",
        taller_idx=1,
        tecnico_idx=3,  # Mario Lopez
        descripcion="Reparacion de carroceria por golpe en parachoques.",
        categoria="Chaperia y pintura",
        prioridad="media",
        estado_incidente="en_proceso",
        estado_asignacion="en_camino",
        lat=-17.776900, lng=-63.166400,
        nota_taller="Cliente acepto cotizacion, tecnico en camino.",
        cotizacion_estado="aceptada",
        cotizacion_monto=320.00,
    ))
