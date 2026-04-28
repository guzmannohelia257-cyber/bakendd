"""
Schemas Pydantic para el panel de administrador.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── TALLERES ──────────────────────────────────────────────────────────────────

# ── CATEGORÍAS ────────────────────────────────────────────────────────────────

class CategoriaAdminCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=255)


class CategoriaAdminResponse(BaseModel):
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


# ── TALLERES ──────────────────────────────────────────────────────────────────

class TallerAdminCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., description="Email de acceso del taller")
    password: str = Field(..., min_length=8, description="Contraseña inicial")
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=255)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    capacidad_max: int = Field(5, ge=1, le=100)
    verificado: bool = Field(True, description="Si el taller queda verificado al crearlo")
    categorias: List[int] = Field(default_factory=list, description="IDs de categorías que atiende el taller")


class TallerAdminResponse(BaseModel):
    id_taller: int
    nombre: str
    email: str
    telefono: Optional[str]
    direccion: Optional[str]
    latitud: Optional[float]
    longitud: Optional[float]
    capacidad_max: int
    activo: bool
    verificado: bool
    disponible: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TallerAdminStatsResponse(TallerAdminResponse):
    """Detalle de un taller con estadísticas de rendimiento y ganancias."""
    promedio_estrellas: Optional[float] = None
    total_evaluaciones: int = 0
    total_servicios_completados: int = 0
    comision_total_generada: float = 0.0
    monto_total_procesado: float = 0.0


# ── GANANCIAS ─────────────────────────────────────────────────────────────────

class GananciaMensualRow(BaseModel):
    año: int
    mes: int
    nombre_mes: str
    total_pagos: int
    monto_total_procesado: float
    comision_plataforma: float


class GananciaMensualResponse(BaseModel):
    filas: List[GananciaMensualRow]
    total_comision: float
    total_monto_procesado: float


class GananciaTallerRow(BaseModel):
    id_taller: int
    nombre_taller: str
    email: str
    verificado: bool
    activo: bool
    total_pagos: int
    monto_total: float
    comision_plataforma: float
    promedio_estrellas: Optional[float] = None
    total_evaluaciones: int = 0


class GananciaPorTallerResponse(BaseModel):
    filas: List[GananciaTallerRow]
    total_comision: float
    total_monto: float
    filtro_año: Optional[int] = None
    filtro_mes: Optional[int] = None
