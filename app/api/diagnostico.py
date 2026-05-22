"""Endpoint de diagnóstico de hora del servidor"""
from fastapi import APIRouter, Query, Header, Depends
from datetime import datetime
from app.core.config import get_settings
from app.core.security import verify_token
from app.api.tenants import _require_super_admin
import calendar

router = APIRouter(
    prefix="/diagnostico",
    tags=["Admin"],
    dependencies=[Depends(_require_super_admin)],
)

@router.get("/hora")
def diagnostico_hora():
    """
    Endpoint para verificar la hora del servidor.
    Si hay desajuste de hora entre cliente y servidor, los tokens JWT fallarán.
    """
    settings = get_settings()
    
    return {
        "server_time_utc": datetime.utcnow().isoformat(),
        "server_timezone": "UTC",
        "token_expiration_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "mensaje": "Si el reloj del servidor y cliente no coinciden, los tokens JWT fallarán",
        "solucion": "Sincroniza la hora del dispositivo/emulador con la hora actual"
    }


@router.get("/token")
def diagnostico_token(authorization: str = Header(None)):
    """
    Endpoint para diagnosticar por qué un token es rechazado.
    Envía el token en el header Authorization: Bearer <token>
    """
    
    if not authorization:
        return {
            "error": "No se envió Authorization header",
            "esperado": "Authorization: Bearer <tu_token_aqui>"
        }
    
    # Extraer el token del formato "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {
            "error": "Formato de Authorization inválido",
            "esperado": "Authorization: Bearer <token>",
            "recibido": authorization[:50] + "..." if len(authorization) > 50 else authorization
        }
    
    token = parts[1]
    
    # Intentar verificar el token
    payload = verify_token(token)
    
    if payload is None:
        return {
            "error": "Token inválido o expirado",
            "token_preview": token[:30] + "...",
            "acciones": [
                "1. Verifica que el token no esté expirado",
                "2. Verifica que la SECRET_KEY del cliente sea igual a la del servidor",
                "3. Comprueba que el token fue generado por el endpoint /usuarios/login"
            ]
        }
    
    # Token válido
    exp_timestamp = payload.get('exp')
    exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
    
    # Usar calendar.timegm para evitar problemas de zona horaria en Windows
    now_timestamp = calendar.timegm(datetime.utcnow().timetuple())
    tiempo_restante = int(exp_timestamp - now_timestamp)
    
    return {
        "resultado": "Token válido",
        "payload": {
            "sub": payload.get("sub"),
            "tipo": payload.get("tipo"),
            "exp": exp_datetime.isoformat(),
            "tiempo_restante_segundos": tiempo_restante,
            "tiempo_restante_minutos": tiempo_restante // 60
        },
        "validaciones": {
            "es_usuario": payload.get("tipo") == "usuario",
            "tiene_sub": payload.get("sub") is not None,
            "no_expirado": tiempo_restante > 0
        }
    }

