"""
Esquemas Pydantic para Usuario
Define qué datos recibe la API (requests) y qué retorna (responses)
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ==========================================
# SCHEMAS PARA REGISTRO (POST /usuarios/registro)
# ==========================================

class UsuarioCreate(BaseModel):
    """
    Datos que envía la app móvil (Flutter) para crear una nueva cuenta
    Ejemplo:
    {
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "password": "miPassword123!",
        "telefono": "+57 3001234567"
    }
    """
    nombre: str = Field(..., min_length=3, max_length=100, description="Nombre completo")
    email: EmailStr = Field(..., description="Email único del usuario")
    password: str = Field(..., min_length=8, description="Contraseña (mín 8 caracteres)")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono opcional")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Pérez",
                "email": "juan@example.com",
                "password": "seguro123!",
                "telefono": "+57 3001234567"
            }
        }


# ==========================================
# SCHEMAS PARA RESPUESTAS (HTTP 200)
# ==========================================

class UsuarioResponse(BaseModel):
    """
    Datos que le devolvemos al cliente tras un registro exitoso
    ⚠️ Nota: NUNCA incluir password_hash por seguridad
    """
    id_usuario: int = Field(..., description="ID único del usuario")
    id_rol: int = Field(..., description="ID del rol (1=cliente, 2=taller, etc)")
    nombre: str = Field(..., description="Nombre del usuario")
    email: str = Field(..., description="Email del usuario")
    telefono: Optional[str] = Field(None, description="Teléfono")
    activo: bool = Field(..., description="Si el usuario está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    
    class Config:
        from_attributes = True  # Permite leer desde objetos SQLAlchemy
        json_schema_extra = {
            "example": {
                "id_usuario": 1,
                "id_rol": 1,
                "nombre": "Juan Pérez",
                "email": "juan@example.com",
                "telefono": "+57 3001234567",
                "activo": True,
                "created_at": "2026-04-15T10:30:00"
            }
        }


class RolResponse(BaseModel):
    """
    Datos del Rol de un usuario
    """
    id_rol: int = Field(..., description="ID del rol")
    nombre: str = Field(..., description="Nombre del rol")
    
    class Config:
        from_attributes = True


class UsuarioDetailResponse(UsuarioResponse):
    """
    Respuesta detallada del usuario, incluye información del rol
    """
    rol: RolResponse = Field(..., description="Información del rol del usuario")


# ==========================================
# SCHEMAS PARA LOGIN (POST /usuarios/login)
# ==========================================

class LoginRequest(BaseModel):
    """
    Credenciales para login
    """
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "juan@example.com",
                "password": "seguro123!"
            }
        }


class TokenResponse(BaseModel):
    """
    Respuesta con token JWT tras login exitoso
    """
    access_token: str = Field(..., description="JWT token para autenticación")
    token_type: str = Field(default="bearer", description="Tipo de token")
    usuario: UsuarioResponse = Field(..., description="Datos del usuario autenticado")


# ==========================================
# SCHEMAS PARA EDICIÓN
# ==========================================

class UsuarioUpdate(BaseModel):
    """
    Datos opcionales para editar el perfil del usuario
    Todos los campos son opcionales para permitir ediciones parciales
    """
    nombre: Optional[str] = Field(None, min_length=3, max_length=100, description="Nuevo nombre")
    telefono: Optional[str] = Field(None, max_length=20, description="Nuevo teléfono")
    password: Optional[str] = Field(None, min_length=8, description="Nueva contraseña (mín 8 caracteres)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Pérez Actualizado",
                "telefono": "+57 3105551234",
                "password": "nuevaPassword123!"
            }
        }


# ==========================================
# SCHEMAS PARA RESPUESTAS DE OPERACIONES
# ==========================================

class MensajeResponse(BaseModel):
    """
    Respuesta genérica con un mensaje
    Usado en DELETE y otros endpoints que no retornan datos
    """
    mensaje: str = Field(..., description="Mensaje de respuesta")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mensaje": "El usuario ha sido desactivado correctamente."
            }
        }
