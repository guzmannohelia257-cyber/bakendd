"""
Escenario 02 — taller acepto, tecnico todavia no inicia el traslado.
  estado_incidente  = pendiente
  estado_asignacion = aceptada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_aceptada",
        taller_idx=2,
        tecnico_idx=4,  # Pedro Vargas
        descripcion="Tengo una llanta reventada, estoy varada en el 2do anillo.",
        categoria="llanta",
        prioridad="alta",
        estado_incidente="pendiente",
        estado_asignacion="aceptada",
        lat=-17.781230, lng=-63.181450,
        nota_taller="Solicitud aceptada, asignando tecnico.",
    ))
