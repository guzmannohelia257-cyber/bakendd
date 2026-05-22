"""
Escenario 12 — cotizacion expirada (cliente no respondio a tiempo).
  estado_incidente  = cancelado
  estado_asignacion = cancelada
  cotizacion        = expirada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_cot_expirada",
        taller_idx=1,
        descripcion="Revision general del motor.",
        categoria="Mecanica general",
        prioridad="baja",
        estado_incidente="cancelado",
        estado_asignacion="cancelada",
        lat=-17.788200, lng=-63.205100,
        nota_taller="Validez de la cotizacion expirada.",
        cotizacion_estado="expirada",
        cotizacion_monto=180.00,
        motivo_cancelacion="Cotizacion expirada sin respuesta",
        cancelada_por="sistema",
    ))
