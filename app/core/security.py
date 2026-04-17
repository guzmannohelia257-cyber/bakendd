"""
Funciones de Seguridad: Hash de contraseñas, JWT, Autenticación, etc
"""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import get_settings

# Configurar Argon2 (más moderno que bcrypt, sin problemas de versión)
ph = PasswordHasher()
settings = get_settings()

# ==========================================
# OAUTH2 - ESQUEMA DE AUTENTICACIÓN
# ==========================================
# Le indica a FastAPI dónde debe extraer el token (Authorization: Bearer <token>)
# También es usado por Swagger para crear el botón "Authorize"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usuarios/login")


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando Argon2
    Nunca almacenar contraseñas en texto plano
    """
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash
    """
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un JWT token con los datos proporcionados
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verifica y decodifica un JWT token
    Retorna el payload si es válido, None si no lo es
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ==========================================
# DEPENDENCIA DE AUTENTICACIÓN - EL "GUARDIA"
# ==========================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(lambda: __import__('app.db.session', fromlist=['get_db']).SessionLocal())
):
    """
    Dependencia que:
    1. Extrae el token del Header (Authorization: Bearer <token>)
    2. Valida que sea un JWT válido
    3. Verifica que el usuario existe y está activo
    4. Retorna el usuario actual
    
    Si algo falla → 401 Unauthorized
    
    Se usa así en los endpoints:
    @router.get("/mi-perfil")
    def mi_perfil(current_user: Usuario = Depends(get_current_user)):
        return current_user
    """
    from app.models.user_model import Usuario
    
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el JWT
        payload = verify_token(token)
        if payload is None:
            raise credenciales_exception
        
        # Extraer el email del token (fue guardado como "sub")
        email: str = payload.get("sub")
        if email is None:
            raise credenciales_exception
            
    except JWTError:
        raise credenciales_exception
    
    # Buscar el usuario en la BD
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    
    if usuario is None:
        raise credenciales_exception
    
    # Verificar que esté activo
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario ha sido desactivado"
        )
    
    return usuario
