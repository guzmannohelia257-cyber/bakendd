"""
Escenario 15 — cliente pago y luego se reembolso el cobro (cancelacion tardia).
  estado_incidente  = cancelado
  estado_asignacion = cancelada
  pago              = reembolsado
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_pago_reembolso",
        taller_idx=1,
        tecnico_idx=2,  # Luis Rodriguez
        descripcion="Falla en la transmision, problema diferente al diagnosticado.",
        categoria="motor",
        prioridad="alta",
        estado_incidente="cancelado",
        estado_asignacion="cancelada",
        lat=-17.794100, lng=-63.179900,
        nota_taller="Pago revertido tras cancelacion acordada.",
        motivo_cancelacion="Servicio fuera de alcance del taller",
        cancelada_por="taller",
        pago_estado="reembolsado",
        pago_monto=130.00,
        pago_metodo="tarjeta",
    ))
