"""
Schemas Pydantic para Taller y Técnicos.

Importante:
- El Taller se autentica por su propia cuenta (email + password).
- El Técnico NO se autentica: es solo un registro operativo del taller.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# Taller

class TallerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TallerUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=255)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    capacidad_max: Optional[int] = Field(None, ge=1)


class TallerResponse(BaseModel):
    id_taller: int
    nombre: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    capacidad_max: int
    tarifa_traslado: float
    disponible: bool
    activo: bool
    verificado: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TallerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    taller: TallerResponse


# Técnico

class TecnicoCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)


class TecnicoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    disponible: Optional[bool] = None
    activo: Optional[bool] = None


class TecnicoResponse(BaseModel):
    id_tecnico: int
    id_taller: int
    nombre: str
    telefono: Optional[str] = None
    disponible: bool
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TecnicoLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TecnicoTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tecnico: TecnicoResponse


# Asignaciones (lado taller)

class AceptarAsignacionRequest(BaseModel):
    id_usuario: Optional[int] = Field(None, description="Usuario técnico (rol=3) asignado al trabajo")
    eta_minutos: Optional[int] = Field(None, ge=1, le=600, description="Tiempo estimado de llegada en minutos")
    nota: Optional[str] = Field(None, max_length=500, description="Nota opcional del taller al cliente")


class RechazarAsignacionRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500, description="Razón del rechazo")


class IniciarViajeRequest(BaseModel):
    """Técnico sale hacia el cliente (aceptada → en_camino). Puede reportar su ubicación."""
    latitud_tecnico: Optional[float] = Field(None, description="Ubicación actual del técnico (latitud)")
    longitud_tecnico: Optional[float] = Field(None, description="Ubicación actual del técnico (longitud)")


class CompletarAsignacionRequest(BaseModel):
    """Servicio completado (en_camino → completada). El técnico reporta el cobro final y detalles del trabajo."""
    model_config = ConfigDict(populate_by_name=True)

    costo_final: Optional[float] = Field(
        None,
        ge=0,
        alias="costo_estimado",
        description="Cobro final acordado; se guarda en asignacion.costo_estimado por compatibilidad",
    )
    resumen_trabajo: Optional[str] = Field(None, max_length=1000, description="Descripción del trabajo realizado")


class ClienteMini(BaseModel):
    id_usuario: int
    nombre: str
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class VehiculoMiniT(BaseModel):
    id_vehiculo: int
    placa: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True


class CategoriaMiniT(BaseModel):
    id_categoria: int
    nombre: str

    class Config:
        from_attributes = True


class PrioridadMiniT(BaseModel):
    id_prioridad: int
    nivel: str
    orden: int

    class Config:
        from_attributes = True


class EstadoAsignacionMiniT(BaseModel):
    id_estado_asignacion: int
    nombre: str

    class Config:
        from_attributes = True


class IncidenteParaTaller(BaseModel):
    """Información del incidente que el taller necesita ver"""
    id_incidente: int
    descripcion_usuario: Optional[str] = None
    resumen_ia: Optional[str] = None
    latitud: float
    longitud: float
    created_at: datetime

    usuario: ClienteMini
    vehiculo: VehiculoMiniT
    categoria: Optional[CategoriaMiniT] = None
    prioridad: Optional[PrioridadMiniT] = None

    class Config:
        from_attributes = True


class EvidenciaMiniT(BaseModel):
    """Evidencia del incidente (imagen, audio, texto)"""
    id_evidencia: int
    id_tipo_evidencia: int
    url_archivo: str
    transcripcion_audio: Optional[str] = None
    descripcion_ia: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IncidenteParaTecnico(IncidenteParaTaller):
    """Incidente con evidencias del cliente, para vista del técnico"""
    evidencias: List[EvidenciaMiniT] = []


class UbicacionTecnicoRequest(BaseModel):
    """Actualización de ubicación en tiempo real del técnico"""
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)


class AsignacionTallerResponse(BaseModel):
    """Asignación vista desde el taller, con info del incidente y cliente"""
    id_asignacion: int
    id_incidente: int
    id_taller: int
    id_usuario: Optional[int] = None  # Usuario técnico asignado al trabajo
    id_estado_asignacion: int
    eta_minutos: Optional[int] = None
    costo_estimado: Optional[float] = None
    costo_final: Optional[float] = None
    nota_taller: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Indica si el cliente ya pagó el servicio de este incidente.
    # Default False para no romper si el endpoint no lo setea.
    pagado: bool = False

    estado: EstadoAsignacionMiniT
    incidente: IncidenteParaTaller

    class Config:
        from_attributes = True


# Asignaciones (vista del técnico)

class UbicacionIncidente(BaseModel):
    """Ubicación GPS del incidente"""
    latitud: float
    longitud: float
    created_at: datetime

    class Config:
        from_attributes = True


class TecnicoAsignacionResponse(BaseModel):
    """Asignación vista desde el técnico, con detalles completos del trabajo"""
    id_asignacion: int
    id_incidente: int
    id_usuario: int  # Usuario técnico
    id_taller: int
    eta_minutos: Optional[int] = None
    # Tolerancia global del SLA de llegada (configuracion_plataforma.sla_tolerancia_min).
    # No es columna de la asignacion: el router la adjunta antes de responder para
    # que el tecnico calcule la hora maxima de llegada = eta_minutos + tolerancia.
    sla_tolerancia_min: Optional[int] = None
    costo_estimado: Optional[float] = None
    costo_final: Optional[float] = None
    nota_taller: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    estado: EstadoAsignacionMiniT
    incidente: IncidenteParaTecnico  # Incluye las evidencias del cliente

    class Config:
        from_attributes = True


# Genéricos

class MensajeResponse(BaseModel):
    mensaje: str


# Usuario_taller (técnicos del taller)

class UsuarioTallerCreate(BaseModel):
    """Crear un técnico (usuario rol=3) vinculado a un taller"""
    nombre: str = Field(..., min_length=3, max_length=100, description="Nombre del técnico")
    email: EmailStr = Field(..., description="Email único para login")
    password: str = Field(..., min_length=8, description="Password para el técnico")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono de contacto")


class UsuarioTallerUpdate(BaseModel):
    """Actualizar datos de un técnico del taller"""
    disponible: Optional[bool] = Field(None, description="¿El técnico está disponible?")
    latitud: Optional[float] = Field(None, description="Ubicación actual del técnico (latitud)")
    longitud: Optional[float] = Field(None, description="Ubicación actual del técnico (longitud)")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono de contacto")


class UsuarioTallerResponse(BaseModel):
    """Respuesta de un técnico vinculado a un taller"""
    id_usuario_taller: int
    id_usuario: int
    id_taller: int
    disponible: bool
    activo: bool
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    created_at: datetime
    
    # Info del usuario
    nombre: str
    email: str
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class UsuarioTallerListResponse(BaseModel):
    """Respuesta simplificada para listar técnicos"""
    id_usuario_taller: int
    id_usuario: int
    nombre: str
    email: str
    telefono: Optional[str] = None
    disponible: bool
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Servicios del taller

class TallerServicioCreate(BaseModel):
    id_categoria: int = Field(..., gt=0)
    servicio_movil: bool = False
    tarifa_base: Optional[float] = Field(None, ge=0)
    tiempo_estimado_min: Optional[int] = Field(None, ge=0, le=60 * 24)


class TallerServicioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_taller_servicio: int
    id_taller: int
    id_categoria: int
    servicio_movil: bool
    tarifa_base: Optional[float] = None
    tiempo_estimado_min: Optional[int] = None


class TallerConServicios(TallerResponse):
    """Taller incluyendo lista de servicios que ofrece."""
    servicios: List[TallerServicioResponse] = []


class ActualizarServiciosTallerRequest(BaseModel):
    """
    Reemplaza la lista completa de servicios del taller (idempotente).
    """
    servicios: List[TallerServicioCreate]


class TallerCompatibleResponse(TallerResponse):
    """Taller candidato para un incidente, incluye distancia y desglose."""
    distancia_km: Optional[float] = None
    tarifa_base: Optional[float] = None
    monto_traslado: Optional[float] = None  # tarifa_traslado_taller * distancia_km
    total_estimado: Optional[float] = None  # tarifa_base + monto_traslado
    tiempo_reparacion_min: Optional[int] = None  # TallerServicio.tiempo_estimado_min
    eta_llegada_min: Optional[int] = None  # distancia_km / VELOCIDAD_DEFAULT_KMH * 60
    rating_promedio: Optional[float] = None
