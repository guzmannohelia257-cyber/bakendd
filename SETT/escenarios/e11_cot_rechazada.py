"""
Escenario 11 — cliente rechazo la cotizacion (precio muy alto).
  estado_incidente  = cancelado
  estado_asignacion = cancelada
  cotizacion        = rechazada
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_cot_rechazada",
        taller_idx=1,
        descripcion="Falla del computador del auto.",
        categoria="Servicio electronico",
        prioridad="media",
        estado_incidente="cancelado",
        estado_asignacion="cancelada",
        lat=-17.819400, lng=-63.193700,
        nota_taller="Cliente no acepto cotizacion.",
        cotizacion_estado="rechazada",
        cotizacion_monto=450.00,
        motivo_cancelacion="Costo fuera de presupuesto",
        cancelada_por="cliente",
    ))
