"""
Escenario 14 — servicio terminado pero el pago fallo (tarjeta rechazada).
  estado_incidente  = atendido
  estado_asignacion = completada
  pago              = fallido
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_pago_fallido",
        taller_idx=2,
        tecnico_idx=4,  # Pedro Vargas
        descripcion="Llanta cambiada, cliente intenta pagar.",
        categoria="llanta",
        prioridad="media",
        estado_incidente="atendido",
        estado_asignacion="completada",
        lat=-17.815700, lng=-63.198800,
        nota_taller="Pago intentado dos veces sin exito.",
        pago_estado="fallido",
        pago_monto=70.00,
        pago_metodo="tarjeta",
        evaluacion_estrellas=3,
        evaluacion_comentario="El servicio bien, problemas con la pasarela de pago.",
    ))
