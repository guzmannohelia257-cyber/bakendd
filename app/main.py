"""
Aplicación Principal de FastAPI
Punto de entrada: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
import os
from app.api import (
    users_router, talleres_router, vehiculos_router,
    incidencias_router, evidencias_router, tecnicos_router,
    notificaciones_router, mensajes_router, pagos_router,
    admin_router,
)
from app.db.session import engine, Base
# Importar el paquete de modelos registra todas las tablas en Base.metadata
# antes de llamar a create_all.
import app.models  # noqa: F401

# Obtener configuración
settings = get_settings()

# Crear las tablas en la base de datos (si no existen)
# En producción, usar Alembic para migraciones
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

# ==========================================
# MIDDLEWARE: CORS (Cross-Origin Resource Sharing)
# ==========================================
# Permite que Angular (Web), Flutter (Mobile) y otros clientes
# se conecten a esta API desde diferentes orígenes.
# 
# DESARROLLO: allow_origins=["*"] (cualquier origen)
# PRODUCCIÓN: allow_origins=["https://tudominio.com", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # ✅ Angular en puerto 4200
              # ✅ Flutter (iOS/Android)
              # ✅ Postman/Insomnia
              # En producción, ser más restrictivo
    ],
    allow_credentials=True,  # Permite enviar cookies/tokens
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Métodos HTTP permitidos
    allow_headers=["*"],  # Permite autorización (Bearer tokens)
    max_age=3600,  # Cache de preflight requests (segundos)
)

# ==========================================
# REGISTRAR ROUTERS
# ==========================================
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

# Importar y registrar router de diagnóstico
from app.api.diagnostico import router as diagnostico_router
app.include_router(diagnostico_router)

# ==========================================
# ENDPOINT DE PRUEBA
# ==========================================

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


# ==========================================
# MANEJO DE ERRORES GLOBAL
# ==========================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Captura excepciones no manejadas
    Evita exponer detalles internos en producción
    """
    if settings.DEBUG:
        raise exc
    
    return {
        "detail": "Error interno del servidor",
        "status_code": 500
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=settings.DEBUG,
        log_level="info"
    )
