"""
Escenario 07 — cliente cancelo antes de que el tecnico llegara.
  estado_incidente  = cancelado
  estado_asignacion = cancelada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_cancelado",
        taller_idx=2,
        tecnico_idx=5,  # Diego Mamani
        descripcion="Ya consegui ayuda de un familiar, gracias.",
        categoria="otros",
        prioridad="baja",
        estado_incidente="cancelado",
        estado_asignacion="cancelada",
        lat=-17.823100, lng=-63.205400,
        nota_taller="Cliente cancelo antes de la llegada del tecnico.",
        motivo_cancelacion="Cliente resolvio por su cuenta",
        cancelada_por="cliente",
    ))
