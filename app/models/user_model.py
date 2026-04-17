"""
Modelos SQLAlchemy para Usuario y Rol
Estos modelos representan las tablas de PostgreSQL
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Rol(Base):
    """
    Tabla: rol
    Define los roles del sistema: cliente, taller, tecnico, admin
    """
    __tablename__ = "rol"
    
    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)  
    # cliente | taller | tecnico | admin
    
    # Relación bidireccional - un Rol tiene muchos Usuarios
    usuarios = relationship("Usuario", back_populates="rol", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Rol(id={self.id_rol}, nombre='{self.nombre}')>"


class Usuario(Base):
    """
    Tabla: usuario
    Usuarios de la app móvil (clientes principalmente)
    """
    __tablename__ = "usuario"
    
    id_usuario = Column(Integer, primary_key=True, index=True)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), nullable=False)
    
    # Datos personales
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    
    # Seguridad - NUNCA devolver en respuestas JSON
    password_hash = Column(String(255), nullable=False)  # Hasheado con bcrypt
    
    # Notificaciones
    push_token = Column(String(255), nullable=True)  # Token FCM/APNs para push notifications
    
    # Estado
    activo = Column(Boolean, default=True, nullable=False)
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación - muchos Usuarios pertenecen a un Rol
    rol = relationship("Rol", back_populates="usuarios")
    
    def __repr__(self):
        return f"<Usuario(id={self.id_usuario}, email='{self.email}', rol_id={self.id_rol})>"
