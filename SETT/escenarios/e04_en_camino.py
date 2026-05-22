"""
Escenario 04 — tecnico ya viaja al sitio.
  estado_incidente  = en_proceso
  estado_asignacion = en_camino
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_en_camino",
        taller_idx=1,
        tecnico_idx=2,  # Luis Rodriguez
        descripcion="Falla del motor en plena via. Sale humo del cofre.",
        categoria="motor",
        prioridad="critica",
        estado_incidente="en_proceso",
        estado_asignacion="en_camino",
        lat=-17.795020, lng=-63.190100,
        nota_taller="Tecnico en camino, ETA 20 min.",
    ))
