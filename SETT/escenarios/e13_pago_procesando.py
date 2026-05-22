"""
Escenario 13 — servicio listo, pago en procesamiento con Stripe.
  estado_incidente  = atendido
  estado_asignacion = completada
  pago              = procesando
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_pago_procesando",
        taller_idx=0,
        tecnico_idx=0,  # Juan Perez
        descripcion="Bateria sustituida, pago en proceso por tarjeta.",
        categoria="bateria",
        prioridad="media",
        estado_incidente="atendido",
        estado_asignacion="completada",
        lat=-17.802000, lng=-63.182000,
        nota_taller="Servicio completado, cobro en transito.",
        pago_estado="procesando",
        pago_monto=110.00,
        pago_metodo="tarjeta",
        evaluacion_estrellas=4,
        evaluacion_comentario="Buen servicio, atencion rapida.",
    ))
