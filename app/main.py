"""
Aplicación Principal de FastAPI
Punto de entrada: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import get_settings
import os
from app.api import (
    users_router, talleres_router, vehiculos_router,
    incidencias_router, evidencias_router, tecnicos_router,
    notificaciones_router, mensajes_router, pagos_router,
    admin_router, tenants_router, catalogos_router, cotizaciones_router, asignaciones_router, kpis_router,
    adendas_router, reportes_router, tracking_publico_router,
)
from app.db.session import engine, Base
# Importar el paquete de modelos registra todas las tablas en Base.metadata
# antes de llamar a create_all.
import app.models  # noqa: F401
from app.core.tenant_middleware import TenantContextMiddleware
from app.core.tenant_filter import install_tenant_filter
from app.core.rate_limit import limiter
from app.realtime import pubsub_broker
from app.realtime.endpoints import router as ws_router

# Obtener configuración
settings = get_settings()

# Crear las tablas en la base de datos (si no existen)
# DEPRECATED: usar Alembic (`alembic upgrade head`). Se mantiene solo como
# escape hatch para sandboxes aislados.
if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)

# Inicializar aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API inteligente para reportar emergencias vehiculares",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware CORS (Cross-Origin Resource Sharing)
# CORS_ORIGINS en .env (separados por coma). Si está vacío y DEBUG=True se
# permite "*" pero SIN credentials (combinación ilegal por spec).
# Producción: poblar SIEMPRE CORS_ORIGINS con dominios exactos.
_origins_raw = (settings.CORS_ORIGINS or "").strip()
if _origins_raw:
    cors_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    allow_credentials = True
elif settings.DEBUG:
    cors_origins = ["*"]
    allow_credentials = False  # "*" + credentials no es válido en el spec
else:
    # Producción sin CORS_ORIGINS: no permitimos cross-origin (mejor fallar)
    cors_origins = []
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    # Content-Disposition se expone para que el front lea el nombre del archivo
    # en las descargas de reportes (PDF/Excel) servidas por StreamingResponse.
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

# Rate limiting básico (SlowAPI)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Multi-tenant (Fase 1)
# Middleware: extrae id_tenant del JWT a ContextVar por request.
# Filtro global: añade WHERE id_tenant=... a queries de modelos tenant-scoped.
# include_legacy=True deja pasar filas viejas con id_tenant IS NULL durante
# el período de backfill. Una vez backfilleadas, cambiar a False.
app.add_middleware(TenantContextMiddleware)
# include_legacy=False: tras backfill (scripts/backfill_tenants.py) + migración
# 0003, no quedan filas legacy en taller. Las tablas transaccionales pueden
# tener id_tenant NULL solo en flujos públicos (cliente final reportando), pero
# esos no usan filtro de tenant porque current_tenant=None.
install_tenant_filter(include_legacy=False)

# Registrar routers
app.include_router(users_router)
app.include_router(talleres_router)
app.include_router(tecnicos_router)
app.include_router(vehiculos_router)
app.include_router(incidencias_router)
app.include_router(evidencias_router)
app.include_router(notificaciones_router)
app.include_router(mensajes_router)
app.include_router(pagos_router)
app.include_router(admin_router)
app.include_router(tenants_router)
app.include_router(catalogos_router)
app.include_router(cotizaciones_router)
app.include_router(asignaciones_router)
app.include_router(kpis_router)
app.include_router(adendas_router)
app.include_router(reportes_router)
app.include_router(tracking_publico_router)
app.include_router(ws_router)

from app.api.diagnostico import router as diagnostico_router
app.include_router(diagnostico_router)

# Endpoint de prueba

@app.get("/", tags=["Health Check"])
def read_root():
    """
    Endpoint de prueba para verificar que la API está en línea
    """
    return {
        "api": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online ✅",
        "message": "Bienvenido a la API de Emergencias Vehiculares",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Healthcheck para balanceadores de carga
    """
    return {
        "status": "healthy",
        "database": "connected"
    }


# Manejo de errores global

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Captura excepciones no manejadas. Evita exponer detalles internos en
    produccion. Debe devolver una Response valida, NO un dict (eso causa
    'dict object is not callable' en Starlette).
    """
    from starlette.responses import JSONResponse
    if settings.DEBUG:
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Demasiadas peticiones"})


@app.on_event("startup")
async def _start_realtime() -> None:
    await pubsub_broker.start()


@app.on_event("shutdown")
async def _stop_realtime() -> None:
    await pubsub_broker.stop()


if __name__ == "__main__":
    import uvicorn
    # Puerto local por defecto = 8001 (el 8000 lo usa otro programa del usuario).
    # En Render, $PORT lo inyecta la plataforma — no afecta producción.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        reload=settings.DEBUG,
        log_level="info"
    )
