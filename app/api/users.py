"""
Router de Usuarios
Endpoints para:
- Registro de nuevas cuentas (CU-01)
- Autenticación y login
- Consulta de perfil protegida
- Edición de perfil protegida
- Dar de baja (baja lógica)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user_model import Usuario, Rol
from app.schemas.user_schema import (
    UsuarioCreate,
    UsuarioResponse,
    UsuarioDetailResponse,
    UsuarioUpdate,
    LoginRequest,
    TokenResponse,
    MensajeResponse
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(
    prefix="/usuarios",
    tags=["Gestión de Usuarios (CU-01)"],
    responses={
        400: {"description": "Bad Request - Validación fallida"},
        404: {"description": "Not Found - Usuario no encontrado"},
        409: {"description": "Conflict - Email ya registrado"}
    }
)


@router.post(
    "/registro",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crea una nueva cuenta de usuario. Email debe ser único."
)
def registrar_usuario(
    user_data: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint para que la app móvil (Flutter) registre un nuevo usuario.
    
    **Request:**
    ```json
    {
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "password": "seguro123!",
        "telefono": "+57 3001234567"
    }
    ```
    
    **Response (201 Created):**
    ```json
    {
        "id_usuario": 1,
        "id_rol": 1,
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "activo": true,
        "created_at": "2026-04-15T10:30:00"
    }
    ```
    """
    
    # 1️⃣ Verificar si el correo ya existe
    usuario_existente = db.query(Usuario).filter(
        Usuario.email == user_data.email
    ).first()
    
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado en el sistema"
        )
    
    # 2️⃣ Hashear la contraseña con bcrypt
    password_hasheada = hash_password(user_data.password)
    
    # 3️⃣ Crear nuevo usuario
    # id_rol = 1 por defecto (cliente)
    nuevo_usuario = Usuario(
        id_rol=1,  # Cliente por defecto
        nombre=user_data.nombre,
        email=user_data.email,
        telefono=user_data.telefono,
        password_hash=password_hasheada,
        activo=True
    )
    
    # 4️⃣ Guardar en la Base de Datos
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return nuevo_usuario


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticarse e iniciar sesión",
    description="Valida email y contraseña, retorna JWT token"
)
def login(
    credenciales: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint para que los usuarios se autentiquen.
    
    **Request:**
    ```json
    {
        "email": "juan@example.com",
        "password": "seguro123!"
    }
    ```
    
    **Response (200 OK):**
    ```json
    {
        "access_token": "eyJhbGc...",
        "token_type": "bearer",
        "usuario": {
            "id_usuario": 1,
            "id_rol": 1,
            "nombre": "Juan Pérez",
            "email": "juan@example.com",
            "activo": true,
            "created_at": "2026-04-15T10:30:00"
        }
    }
    ```
    """
    
    # 1️⃣ Buscar el usuario por email
    usuario = db.query(Usuario).filter(
        Usuario.email == credenciales.email
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    # 2️⃣ Verificar la contraseña
    if not verify_password(credenciales.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    # 3️⃣ Crear JWT token
    access_token = create_access_token(
        data={"sub": usuario.id_usuario, "email": usuario.email}
    )
    
    # 4️⃣ Retornar token y datos del usuario
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario
    }


@router.get(
    "/perfil",
    response_model=UsuarioDetailResponse,
    summary="Obtener mi perfil (protegido)",
    description="Retorna los datos del usuario autenticado. Requiere JWT token."
)
def obtener_mi_perfil(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint protegido para obtener el perfil del usuario autenticado.
    
    **Seguridad:** Requiere enviar el JWT token en el Header:
    ```
    Authorization: Bearer <token>
    ```
    
    **Response (200 OK):**
    ```json
    {
        "id_usuario": 2,
        "id_rol": 1,
        "nombre": "Carlos López",
        "email": "carlos@ejemplo.com",
        "activo": true,
        "created_at": "2026-04-15T16:14:39",
        "rol": {
            "id_rol": 1,
            "nombre": "cliente"
        }
    }
    ```
    """
    return current_user


@router.put(
    "/perfil",
    response_model=UsuarioResponse,
    summary="Editar mi perfil (protegido)",
    description="Actualiza datos del perfil del usuario autenticado. Requiere JWT token."
)
def editar_mi_perfil(
    user_update: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint protegido para que el usuario edite su propio perfil.
    
    **Seguridad:** 
    - Requiere JWT token en el Header: `Authorization: Bearer <token>`
    - Solo puede editar su propio perfil (imposible editar otros usuarios)
    
    **Request:**
    ```json
    {
        "nombre": "Juan Pérez Actualizado",
        "telefono": "+57 3105551234",
        "password": "nuevaPassword123!"
    }
    ```
    
    **Notas:**
    - Todos los campos son opcionales
    - Si se modifica la contraseña, se hasheará automáticamente
    - El email NO se puede cambiar por seguridad
    - El ID se extrae del token (no de la URL)
    
    **Response (200 OK):**
    Retorna los datos actualizados del usuario
    """
    
    # ✅ El usuario ya está verificado por get_current_user
    # ✅ No necesitamos verificar el ID en la URL (está en el token)
    
    # Actualizar solo los campos que se envían
    if user_update.nombre is not None:
        current_user.nombre = user_update.nombre
    
    if user_update.telefono is not None:
        current_user.telefono = user_update.telefono
    
    if user_update.password is not None:
        # Hashear la nueva contraseña con Argon2
        current_user.password_hash = hash_password(user_update.password)
    
    # Guardar cambios
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.delete(
    "/perfil",
    response_model=MensajeResponse,
    summary="Dar de baja mi cuenta (baja lógica, protegido)",
    description="Desactiva la cuenta del usuario autenticado. Requiere JWT token."
)
def dar_de_baja_mi_cuenta(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint protegido para que el usuario se dé de baja a sí mismo.
    
    **Seguridad:**
    - Requiere JWT token en el Header: `Authorization: Bearer <token>`
    - Solo puede darse de baja a sí mismo
    - El ID se extrae del token (no de la URL)
    
    **Implementa Baja Lógica (Punto de examen):**
    En lugar de eliminar físicamente al usuario de la BD (lo que rompería
    la trazabilidad de incidentes, asignaciones y pagos), marcamos 
    activo=False. Así se preserva la integridad referencial.
    
    **Response (200 OK):**
    ```json
    {
        "mensaje": "Tu cuenta ha sido desactivada correctamente. Tus datos se mantienen para trazabilidad."
    }
    ```
    """
    
    # ✅ El usuario ya está verificado y activo por get_current_user
    
    # BAJA LÓGICA: Cambiar activo a False en lugar de DELETE
    current_user.activo = False
    
    db.commit()
    
    return {
        "mensaje": f"Tu cuenta ({current_user.email}) ha sido desactivada correctamente. "
                   f"Tus datos se mantienen para trazabilidad de incidentes y pagos."
    }
