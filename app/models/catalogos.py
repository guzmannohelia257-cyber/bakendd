"""
Catálogos (tablas de diccionario) del sistema.
Valores fijos referenciados por las entidades principales.
"""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class Rol(Base):
    __tablename__ = "rol"

    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)  # cliente | taller | tecnico | admin

    usuarios = relationship("Usuario", back_populates="rol")


class EstadoIncidente(Base):
    __tablename__ = "estado_incidente"

    id_estado = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)  # pendiente | en_proceso | atendido | cancelado
    descripcion = Column(String(200), nullable=True)


class CategoriaProblema(Base):
    __tablename__ = "categoria_problema"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String(200), nullable=True)
    icono_url = Column(String(255), nullable=True)
    codigo = Column(String(50), nullable=True, unique=True)
    requiere_cotizacion = Column(Boolean, default=False, nullable=False)


class Prioridad(Base):
    __tablename__ = "prioridad"

    id_prioridad = Column(Integer, primary_key=True, index=True)
    nivel = Column(String(50), nullable=False)  # baja | media | alta | critica
    orden = Column(Integer, nullable=False)


class EstadoAsignacion(Base):
    __tablename__ = "estado_asignacion"

    id_estado_asignacion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)


class TipoEvidencia(Base):
    __tablename__ = "tipo_evidencia"

    id_tipo_evidencia = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)  # imagen | audio | texto


class MetodoPago(Base):
    __tablename__ = "metodo_pago"

    id_metodo_pago = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)


class EstadoPago(Base):
    __tablename__ = "estado_pago"

    id_estado_pago = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
