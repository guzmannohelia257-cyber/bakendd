"""
Modelo multi-tenant.

TENANT       : Organizacion duenia de uno o mas talleres (sucursales).
PLAN         : Planes de suscripcion del SaaS (Basico, Pro, Enterprise...).
SUSCRIPCION  : Vinculo Tenant <-> Plan, con estado y fechas.
TENANT_USER  : Usuarios "internos" del tenant (admin org, contador, etc.).
               Distintos de clientes finales (rol cliente).

Notas de disenio:
- Cliente final NO pertenece a tenant: puede solicitar servicio a cualquier taller
  publicado en la plataforma.
- Taller pertenece a UN tenant (id_tenant en taller, nullable durante migracion).
- Datos transaccionales heredan id_tenant del taller al que se asignan.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Plan(Base):
    __tablename__ = "plan"

    id_plan = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True)  # free | pro | enterprise
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(500), nullable=True)

    precio_mensual = Column(Numeric(10, 2), nullable=False, default=0)
    moneda = Column(String(3), nullable=False, default="USD")

    # Límites del plan
    max_talleres = Column(Integer, nullable=False, default=1)
    max_tecnicos = Column(Integer, nullable=False, default=5)
    max_incidentes_mes = Column(Integer, nullable=True)  # None = ilimitado

    # Feature flags simples (extender según se necesite)
    feature_websockets = Column(Boolean, default=False, nullable=False)
    feature_kpis_avanzados = Column(Boolean, default=False, nullable=False)
    feature_reportes_ia = Column(Boolean, default=False, nullable=False)

    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Tenant(Base):
    """
    Organizacion duena de talleres dentro del SaaS.
    """
    __tablename__ = "tenant"

    id_tenant = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)  # url-friendly
    nombre = Column(String(150), nullable=False)
    email_contacto = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=True)

    activo = Column(Boolean, default=True, nullable=False)
    suspendido = Column(Boolean, default=False, nullable=False)  # billing/abuse

    # Porcentajes de compensación por cancelación, configurables por tenant.
    # Se aplican sobre taller.tarifa_traslado para calcular el monto que recibe
    # el taller cuando el cliente cancela en cada estado.
    pct_cancel_pendiente = Column(Integer, default=0, nullable=False, server_default="0")
    pct_cancel_aceptada = Column(Integer, default=50, nullable=False, server_default="50")
    pct_cancel_en_camino = Column(Integer, default=100, nullable=False, server_default="100")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    talleres = relationship("Taller", back_populates="tenant")
    suscripciones = relationship("Suscripcion", back_populates="tenant", cascade="all, delete-orphan")
    miembros = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")


class Suscripcion(Base):
    __tablename__ = "suscripcion"

    id_suscripcion = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)
    id_plan = Column(Integer, ForeignKey("plan.id_plan"), nullable=False)

    estado = Column(String(30), nullable=False, default="trial")  # trial | activa | morosa | cancelada
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)

    inicio = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    fin = Column(DateTime(timezone=True), nullable=True)  # None = activa

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="suscripciones")
    plan = relationship("Plan")


class TenantUser(Base):
    """
    Usuarios internos de un tenant (no son clientes finales).
    Rol dentro del tenant: owner, admin, operador, contador, etc.
    """
    __tablename__ = "tenant_user"
    __table_args__ = (
        UniqueConstraint("id_tenant", "id_usuario", name="uq_tenant_user"),
    )

    id_tenant_user = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)

    rol_tenant = Column(String(30), nullable=False, default="operador")  # owner | admin | operador
    activo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="miembros")
    usuario = relationship("Usuario")
