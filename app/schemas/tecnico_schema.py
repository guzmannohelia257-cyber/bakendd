"""
Schemas para el flujo de login multi-tenant del tecnico (M9).
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TallerPublicoMini(BaseModel):
    """Vista publica de un taller para el selector pre-login."""
    model_config = ConfigDict(from_attributes=True)

    id_taller: int
    nombre: str
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class TecnicoLoginConTallerRequest(BaseModel):
    """Login del tecnico contra un taller especifico."""
    email: EmailStr
    password: str = Field(..., min_length=1)
    id_taller: int = Field(..., gt=0)


class TallerActivoInfo(BaseModel):
    """Info del taller activo embebida en la respuesta de login."""
    id_taller: int
    id_tenant: int
    nombre: str


class UsuarioMini(BaseModel):
    """Datos minimos del usuario para devolver en login."""
    id_usuario: int
    nombre: str
    email: str


class TecnicoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioMini
    taller_activo: TallerActivoInfo


class CambiarTallerResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    taller_activo: TallerActivoInfo
