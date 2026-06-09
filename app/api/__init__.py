"""
Routers de la aplicación
"""
from app.api.users import router as users_router
from app.api.talleres import router as talleres_router
from app.api.vehiculos import router as vehiculos_router
from app.api.incidencias import router as incidencias_router
from app.api.evidencias import router as evidencias_router
from app.api.tecnicos import router as tecnicos_router
from app.api.notificaciones import router as notificaciones_router
from app.api.mensajes import router as mensajes_router
from app.api.pagos import router as pagos_router
from app.api.admin import router as admin_router
from app.api.tenants import router as tenants_router
from app.api.catalogos import router as catalogos_router
from app.api.cotizaciones import router as cotizaciones_router
from app.api.asignaciones import router as asignaciones_router
from app.api.kpis import router as kpis_router
from app.api.adendas import router as adendas_router
from app.api.reportes import router as reportes_router
from app.api.tracking_publico import router as tracking_publico_router

__all__ = [
    "users_router",
    "talleres_router",
    "vehiculos_router",
    "incidencias_router",
    "evidencias_router",
    "tecnicos_router",
    "notificaciones_router",
    "mensajes_router",
    "pagos_router",
    "admin_router",
    "tenants_router",
    "catalogos_router",
    "cotizaciones_router",
    "asignaciones_router",
    "kpis_router",
    "adendas_router",
    "reportes_router",
    "tracking_publico_router",
]
