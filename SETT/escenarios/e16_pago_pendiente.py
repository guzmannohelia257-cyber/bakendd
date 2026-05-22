"""
Escenario 16 — servicio terminado, factura emitida, cobro aun pendiente.
  estado_incidente  = atendido
  estado_asignacion = completada
  pago              = pendiente
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_pago_pendiente",
        taller_idx=0,
        tecnico_idx=1,  # Carlos Gomez
        descripcion="Cambio de cerradura completado, factura aun por cobrar.",
        categoria="llaves",
        prioridad="media",
        estado_incidente="atendido",
        estado_asignacion="completada",
        lat=-17.798200, lng=-63.190100,
        nota_taller="Servicio listo, esperando confirmacion de pago del cliente.",
        pago_estado="pendiente",
        pago_monto=65.00,
        pago_metodo="qr",
        evaluacion_estrellas=5,
        evaluacion_comentario="Servicio excelente, pagare cuando llegue a casa.",
    ))
