"""
Script para Poblar Usuarios por Roles
Crea 4 usuarios de ejemplo para pruebas según la guía de LOGIN_POR_ROLES.md

Ejecución:
python -m scripts.seed_usuarios
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.user_model import Usuario, Rol
from app.core.security import hash_password

# Crear las tablas si no existen
Base.metadata.create_all(bind=engine)

def crear_usuarios_seed():
    """
    Crea 4 usuarios de ejemplo:
    1. Cliente (Conductor)
    2. Técnico (Mecánico)
    3. Taller (Gerente)
    4. Admin (Sistema)
    """
    db: Session = SessionLocal()
    
    try:
        # Verificar que existan los roles
        print("✓ Verificando roles...")
        roles = db.query(Rol).all()
        
        if not roles:
            print("❌ Error: No hay roles en la base de datos")
            print("   Primero ejecuta: python init_roles.sql")
            return False
        
        print(f"✓ Encontrados {len(roles)} roles")
        
        # Datos de usuarios a crear
        usuarios_seed = [
            {
                "nombre": "Juan Conductor",
                "email": "conductor@ejemplo.com",
                "password": "miPassword123!",
                "telefono": "+57 3001234567",
                "id_rol": 1,  # Cliente
                "descripcion": "👨 Cliente (Conductor) - Flutter"
            },
            {
                "nombre": "Juan Pérez - Técnico",
                "email": "tecnico.juan@taller.com",
                "password": "password456!",
                "telefono": "+57 3105551111",
                "id_rol": 3,  # Técnico
                "descripcion": "🔧 Técnico (Mecánico) - Flutter"
            },
            {
                "nombre": "Carlos - Gerente Taller",
                "email": "gerente@tallerexcelente.com",
                "password": "gerente789!",
                "telefono": "+57 3105552222",
                "id_rol": 2,  # Taller
                "descripcion": "🏭 Taller (Gerente) - Angular"
            },
            {
                "nombre": "Administrador Sistema",
                "email": "admin@plataforma.com",
                "password": "admin2026!",
                "telefono": "+57 3105553333",
                "id_rol": 4,  # Admin
                "descripcion": "👨‍💼 Admin (Sistema) - Angular"
            },
        ]
        
        # Crear los usuarios
        usuarios_creados = 0
        for usuario_data in usuarios_seed:
            # Verificar si ya existe
            usuario_existente = db.query(Usuario).filter(
                Usuario.email == usuario_data["email"]
            ).first()
            
            if usuario_existente:
                print(f"⚠️  Ya existe: {usuario_data['email']}")
                continue
            
            # Crear nuevo usuario
            nuevo_usuario = Usuario(
                nombre=usuario_data["nombre"],
                email=usuario_data["email"],
                password_hash=hash_password(usuario_data["password"]),
                telefono=usuario_data["telefono"],
                id_rol=usuario_data["id_rol"],
                activo=True
            )
            
            db.add(nuevo_usuario)
            usuarios_creados += 1
            print(f"✓ {usuario_data['descripcion']}")
            print(f"  📧 {usuario_data['email']}")
            print(f"  🔑 Contraseña: {usuario_data['password']}")
            print()
        
        # Guardar en la BD
        if usuarios_creados > 0:
            db.commit()
            print(f"✅ {usuarios_creados} usuario(s) creado(s) exitosamente\n")
        else:
            print("ℹ️  Todos los usuarios ya existen\n")
        
        # Mostrar todos los usuarios
        print("=" * 60)
        print("📋 USUARIOS EN LA BASE DE DATOS")
        print("=" * 60)
        todos_usuarios = db.query(Usuario).all()
        for usuario in todos_usuarios:
            rol_nombre = db.query(Rol).filter(Rol.id_rol == usuario.id_rol).first()
            print(f"ID: {usuario.id_usuario} | {usuario.nombre}")
            print(f"   📧 {usuario.email}")
            print(f"   👤 Rol: {rol_nombre.nombre if rol_nombre else 'Desconocido'}")
            print(f"   ✓ Activo: {'Sí' if usuario.activo else 'No'}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🌱 SCRIPT DE POBLACIÓN DE USUARIOS")
    print("=" * 60 + "\n")
    
    exito = crear_usuarios_seed()
    
    if exito:
        print("=" * 60)
        print("🎉 ¡Usuarios listos para pruebas!")
        print("=" * 60)
        print("\n📱 FLUTTER - Prueba con:")
        print("   1. Cliente: conductor@ejemplo.com / miPassword123!")
        print("   2. Técnico: tecnico.juan@taller.com / password456!")
        print("\n🌐 ANGULAR - Prueba con:")
        print("   1. Taller: gerente@tallerexcelente.com / gerente789!")
        print("   2. Admin: admin@plataforma.com / admin2026!")
        print("\n🔗 URL de login: POST http://localhost:8000/usuarios/login")
        print("📖 Documentación: http://localhost:8000/docs\n")
    else:
        print("\n❌ El script no se completó correctamente")
        exit(1)
