"""
Escenario 05 — tecnico ya llego al sitio del incidente.
  estado_incidente  = en_proceso
  estado_asignacion = llegado
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_llegado",
        taller_idx=0,
        tecnico_idx=1,  # Carlos Gomez
        descripcion="Bateria muerta, tecnico ya llego con el cargador.",
        categoria="bateria",
        prioridad="media",
        estado_incidente="en_proceso",
        estado_asignacion="llegado",
        lat=-17.808120, lng=-63.196250,
        nota_taller="Tecnico en sitio, diagnosticando.",
    ))
