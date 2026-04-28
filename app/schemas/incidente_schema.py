"""
Esquemas Pydantic para Incidentes (CU-06)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==========================================
# CREAR INCIDENTE (Lo que envía Flutter)
# ==========================================
class IncidenteCreate(BaseModel):
    """
    Datos que envía el cliente (Flutter) cuando reporta una emergencia.
    El backend asigna automáticamente:
    - id_usuario (del JWT)
    - id_estado=1 (pendiente)
    - id_categoria e id_prioridad se rellenan después por IA
    """
    id_vehiculo: int = Field(..., description="ID del vehículo afectado")
    descripcion_usuario: str = Field(..., description="Descripción del problema reportado por el usuario")
    latitud: float = Field(..., description="Latitud GPS del incidente")
    longitud: float = Field(..., description="Longitud GPS del incidente")


# ==========================================
# RESPUESTA DE INCIDENTE (Lo que responde FastAPI)
# ==========================================
class IncidenteResponse(BaseModel):
    """
    Respuesta completa del incidente al cliente
    """
    id_incidente: int
    id_usuario: int
    id_vehiculo: int
    id_categoria: Optional[int] = None
    id_prioridad: Optional[int] = None
    id_estado: int
    descripcion_usuario: Optional[str] = None
    latitud: float
    longitud: float
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# RESPUESTA CON RELACIONES (Más datos)
# ==========================================
class VehiculoMini(BaseModel):
    """Mini representación del vehículo"""
    id_vehiculo: int
    placa: str
    marca: str
    modelo: str


class EstadoMini(BaseModel):
    """Mini representación del estado"""
    id_estado: int
    nombre: str


class CategoriaMini(BaseModel):
    """Mini representación de categoría"""
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None


class PrioridadMini(BaseModel):
    """Mini representación de prioridad"""
    id_prioridad: int
    nivel: str


# ==========================================
# CANDIDATOS DE ASIGNACIÓN
# ==========================================
class TallerMini(BaseModel):
    """Mini representación del taller para candidatos"""
    id_taller: int
    nombre: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class CandidatoAsignacionResponse(BaseModel):
    """Candidato de asignación para un incidente"""
    id_candidato: int
    id_incidente: int
    id_taller: int
    distancia_km: Optional[float] = None
    score_total: Optional[float] = None
    rating_promedio: Optional[float] = None
    seleccionado: bool = False
    
    taller: TallerMini
    
    class Config:
        from_attributes = True


class EstadoAsignacionMini(BaseModel):
    """Mini representación del estado de asignación"""
    id_estado_asignacion: int
    nombre: str  # pendiente | aceptada | rechazada | en_camino | completada

    class Config:
        from_attributes = True


class AsignacionResponse(BaseModel):
    """Asignación actual del incidente al taller"""
    id_asignacion: int
    id_incidente: int
    id_taller: int
    id_tecnico: Optional[int] = None
    id_estado_asignacion: int
    eta_minutos: Optional[int] = None
    nota_taller: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    taller: TallerMini
    estado: EstadoAsignacionMini

    class Config:
        from_attributes = True


class IncidenteDetalle(BaseModel):
    """
    Respuesta completa con todas las relaciones
    Útil para mostrar en la lista de incidentes
    """
    id_incidente: int
    id_usuario: int
    id_vehiculo: int
    descripcion_usuario: Optional[str] = None
    latitud: float
    longitud: float
    created_at: datetime
    updated_at: datetime

    # Campos de IA (Gemini)
    resumen_ia: Optional[str] = None
    clasificacion_ia_confianza: Optional[float] = None
    requiere_revision_manual: bool = False
    evaluado: bool = False

    # Relaciones
    vehiculo: VehiculoMini
    estado: EstadoMini
    categoria: Optional[CategoriaMini] = None
    prioridad: Optional[PrioridadMini] = None
    candidatos: Optional[List[CandidatoAsignacionResponse]] = None  # ← CANDIDATOS DE ASIGNACIÓN
    asignaciones: List[AsignacionResponse] = []  # ← ASIGNACIONES (estado actual con el taller)

    class Config:
        from_attributes = True


# ==========================================
# CATÁLOGOS
# ==========================================
class CategoriaResponse(BaseModel):
    """Categoría de problema"""
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None
    icono_url: Optional[str] = None

    class Config:
        from_attributes = True


class PrioridadResponse(BaseModel):
    """Nivel de prioridad"""
    id_prioridad: int
    nivel: str
    orden: int = Field(..., description="Orden: 1=baja, 2=media, 3=alta, 4=crítica")

    class Config:
        from_attributes = True


class EstadoIncidenteResponse(BaseModel):
    """Estado de incidente"""
    id_estado: int
    nombre: str

    class Config:
        from_attributes = True


class EvaluacionCreate(BaseModel):
    """Datos para evaluar un servicio (CU-10)"""
    estrellas: int = Field(..., ge=1, le=5, description="Calificación de 1 a 5 estrellas")
    comentario: Optional[str] = Field(None, max_length=500, description="Comentario opcional")


class EvaluacionResponse(BaseModel):
    """Respuesta de evaluación creada"""
    id_evaluacion: int
    id_incidente: int
    id_taller: int
    id_tecnico: Optional[int] = None
    estrellas: int
    comentario: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
