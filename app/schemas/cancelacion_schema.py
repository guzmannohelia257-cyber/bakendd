from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class CancelarAsignacionRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


class CancelacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_asignacion: int
    id_taller: int
    cancelada_at: datetime
    cancelada_por: str
    motivo_cancelacion: str
    compensacion_monto: float
    compensacion_pagada: bool
    nuevo_estado: str
    # True si el monto es 0 porque el tecnico excedio la hora de llegada de la
    # cotizacion (retraso del taller), no porque aun no hubiera salido.
    penalizacion_exonerada_por_retraso: bool = False


class TarifaTrasladoUpdate(BaseModel):
    tarifa_traslado: float = Field(..., ge=0, le=1000)
