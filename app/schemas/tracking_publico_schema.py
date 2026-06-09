"""
Schemas del seguimiento publico (link compartible a terceros).

Estos modelos exponen SOLO datos minimos para que un tercero vea el avance en
vivo: ubicacion del tecnico, ubicacion del cliente y ETA. Deliberadamente NO
incluyen telefono, email, costos, SLA ni ningun otro dato sensible de la
asignacion.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompartirResponse(BaseModel):
    """Respuesta al generar el link publico: el token opaco de la asignacion."""

    token: str


class TecnicoPublico(BaseModel):
    nombre: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    # Marca de tiempo del ultimo ping de ubicacion (para avisar si esta obsoleta).
    actualizado_at: Optional[datetime] = None


class ClientePublico(BaseModel):
    nombre: Optional[str] = None
    latitud: float
    longitud: float


class EtaPublico(BaseModel):
    distancia_km: Optional[float] = None
    eta_minutos: Optional[int] = None


class TrackPublicoResponse(BaseModel):
    estado: str
    tecnico: TecnicoPublico
    cliente: ClientePublico
    eta: Optional[EtaPublico] = None
