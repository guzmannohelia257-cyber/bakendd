from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UbicacionPing(BaseModel):
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = Field(None, ge=0, le=1000)
    velocidad_kmh: Optional[float] = Field(None, ge=0, le=300)
    id_asignacion: Optional[int] = Field(None, description="Si va asociado a una asignacion activa")


class EtaResponse(BaseModel):
    distancia_km: float
    eta_segundos: int
    eta_minutos: int


class UbicacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latitud: float
    longitud: float
    created_at: datetime
    velocidad_kmh: Optional[float] = None
