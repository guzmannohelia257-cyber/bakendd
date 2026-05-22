from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class SolicitarCotizacionesRequest(BaseModel):
    """Cliente pide cotizaciones para un incidente a top-N talleres."""
    radio_km: float = Field(20.0, gt=0, le=100)
    max_talleres: int = Field(3, ge=2, le=5, description="Numero de talleres a invitar")
    validez_horas: int = Field(2, ge=1, le=24, description="Tiempo de validez de las cotizaciones")


class ResponderCotizacionRequest(BaseModel):
    """Taller responde una cotizacion pendiente."""
    monto_servicio: float = Field(..., ge=0)
    monto_repuestos: float = Field(0, ge=0)
    garantia_dias: Optional[int] = Field(None, ge=0, le=365)
    nota: Optional[str] = Field(None, max_length=1000)


class TallerMiniC(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_taller: int
    nombre: str
    telefono: Optional[str] = None


class EstadoCotizacionMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_estado_cotizacion: int
    nombre: str


class CotizacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cotizacion: int
    id_incidente: int
    id_taller: int
    id_estado_cotizacion: int
    monto_servicio: Optional[float] = None
    monto_repuestos: Optional[float] = None
    garantia_dias: Optional[int] = None
    nota: Optional[str] = None
    validez_hasta: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    taller: Optional[TallerMiniC] = None
    estado: Optional[EstadoCotizacionMini] = None

    @property
    def monto_total(self) -> Optional[float]:
        if self.monto_servicio is None:
            return None
        return float(self.monto_servicio) + float(self.monto_repuestos or 0)


class CotizacionesSolicitadasResponse(BaseModel):
    id_incidente: int
    invitadas: int
    cotizaciones: List[CotizacionResponse]
