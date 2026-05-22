"""
TALLER: entidad independiente con su propia autenticación (email + password_hash).
TALLER_SERVICIO: categorías de problemas que atiende cada taller.
USUARIO_TALLER: Vinculación de técnicos (usuarios rol=3) a talleres.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, UniqueConstraint, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Taller(Base):
    __tablename__ = "taller"

    id_taller = Column(Integer, primary_key=True, index=True)
    # Multi-tenant (Fase 1). Post-migracion 0003: NOT NULL.
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)

    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    telefono = Column(String(20), nullable=True)

    password_hash = Column(String(255), nullable=False)  # Los talleres se autentican
    push_token = Column(String(255), nullable=True)

    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    direccion = Column(String(255), nullable=True)

    capacidad_max = Column(Integer, default=5, nullable=False)

    tarifa_traslado = Column(Numeric(10, 2), nullable=False, default=5.00)

    activo = Column(Boolean, default=True, nullable=False)
    verificado = Column(Boolean, default=False, nullable=False)
    disponible = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    servicios = relationship("TallerServicio", back_populates="taller", cascade="all, delete-orphan")
    usuarios_tecnicos = relationship("UsuarioTaller", back_populates="taller", cascade="all, delete-orphan")
    asignaciones = relationship("Asignacion", back_populates="taller")
    evaluaciones = relationship("Evaluacion", back_populates="taller", cascade="all, delete-orphan")
    tenant = relationship("Tenant", back_populates="talleres")


class TallerServicio(Base):
    __tablename__ = "taller_servicio"
    __table_args__ = (
        UniqueConstraint("id_taller", "id_categoria", name="uq_taller_categoria"),
    )

    id_taller_servicio = Column(Integer, primary_key=True, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False)
    id_categoria = Column(Integer, ForeignKey("categoria_problema.id_categoria"), nullable=False)
    servicio_movil = Column(Boolean, default=False, nullable=False)
    tarifa_base = Column(Numeric(10, 2), nullable=True)

    taller = relationship("Taller", back_populates="servicios")
    categoria = relationship("CategoriaProblema")



