"""
Configuracion global de la plataforma (super-admin).

Tabla singleton: contiene una unica fila (id=1) con parametros que aplican a
TODOS los talleres del SaaS, sin distincion de tenant. Hoy solo aloja la
penalizacion por incumplimiento del SLA de llegada (porcentaje y tolerancia en
minutos), pero esta pensada para crecer con futuros ajustes globales.
"""
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func

from app.db.session import Base


class ConfiguracionPlataforma(Base):
    """
    Parametros globales de la plataforma. Se gestiona como singleton (id=1).
    """
    __tablename__ = "configuracion_plataforma"

    id = Column(Integer, primary_key=True, index=True)

    # Penalizacion al taller por incumplir el SLA de llegada.
    # sla_penalizacion_pct : % del monto final del servicio que se cobra.
    # sla_tolerancia_min   : minutos de tolerancia sobre el eta_minutos.
    sla_penalizacion_pct = Column(Integer, default=15, nullable=False, server_default="15")
    sla_tolerancia_min = Column(Integer, default=20, nullable=False, server_default="20")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
