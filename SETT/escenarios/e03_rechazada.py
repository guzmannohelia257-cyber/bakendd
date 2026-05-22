"""
Escenario 03 — taller rechazo la asignacion (capacidad llena).
  estado_incidente  = pendiente   (motor buscara otro taller)
  estado_asignacion = rechazada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_rechazada",
        taller_idx=1,
        descripcion="Choque leve frente a mi auto, no puedo arrancar.",
        categoria="choque",
        prioridad="alta",
        estado_incidente="pendiente",
        estado_asignacion="rechazada",
        lat=-17.815320, lng=-63.188120,
        nota_taller="Sin capacidad disponible en este momento.",
    ))
