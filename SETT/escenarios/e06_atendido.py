"""
Escenario 06 — servicio completado, cliente evaluo con 5 estrellas.
  estado_incidente  = atendido
  estado_asignacion = completada
  pago              = completado
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from SETT.escenarios._base import EscenarioInput, crear_escenario
from SETT.utils import Ctx


def run(db: Session, ctx: Ctx) -> None:
    crear_escenario(db, ctx, EscenarioInput(
        cliente_key="cli_atendido",
        taller_idx=0,
        tecnico_idx=0,  # Juan Perez
        descripcion="Se me perdieron las llaves, no puedo entrar al auto.",
        categoria="llaves",
        prioridad="media",
        estado_incidente="atendido",
        estado_asignacion="completada",
        lat=-17.787500, lng=-63.175800,
        nota_taller="Servicio completado, cerradura sustituida.",
        pago_estado="completado",
        pago_monto=85.50,
        pago_metodo="tarjeta",
        evaluacion_estrellas=5,
        evaluacion_comentario="Excelente atencion y rapidez.",
    ))
