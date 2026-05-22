"""
Modelos SQLAlchemy de la aplicación.
Importar desde aquí garantiza que todas las tablas queden registradas en Base.metadata.
"""
from app.models.tenant import Plan, Tenant, Suscripcion, TenantUser
from app.models.catalogos import (
    Rol,
    EstadoIncidente,
    CategoriaProblema,
    Prioridad,
    EstadoAsignacion,
    TipoEvidencia,
    MetodoPago,
    EstadoPago,
)
from app.models.usuario import Usuario, Vehiculo
from app.models.taller import Taller, TallerServicio
from app.models.usuario_taller import UsuarioTaller
from app.models.incidente import (
    Incidente,
    Asignacion,
    Evidencia,
    HistorialEstadoIncidente,
    HistorialEstadoAsignacion,
    CandidatoAsignacion,
    Evaluacion,
)
from app.models.cotizacion import Cotizacion, EstadoCotizacion
from app.models.transaccional import Notificacion, Pago, Metrica, Mensaje
from app.models.ubicacion import UbicacionTecnico

__all__ = [
    # Multi-tenant
    "Plan",
    "Tenant",
    "Suscripcion",
    "TenantUser",
    # Catálogos
    "Rol",
    "EstadoIncidente",
    "CategoriaProblema",
    "Prioridad",
    "EstadoAsignacion",
    "TipoEvidencia",
    "MetodoPago",
    "EstadoPago",
    # Usuario / vehículos
    "Usuario",
    "Vehiculo",
    # Taller / técnicos
    "Taller",
    "TallerServicio",
    "Tecnico",
    # Incidentes y asignaciones
    "Incidente",
    "Asignacion",
    "Evidencia",
    "HistorialEstadoIncidente",
    "HistorialEstadoAsignacion",
    "CandidatoAsignacion",
    "Evaluacion",
    "Cotizacion",
    "EstadoCotizacion",
    # Transaccional
    "Notificacion",
    "Pago",
    "Metrica",
    "Mensaje",
    "UbicacionTecnico",
]
