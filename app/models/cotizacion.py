"""Cotizaciones: ofertas economicas que un taller envia al cliente
antes de aceptar un incidente, cuando la categoria requiere negociacion previa.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class EstadoCotizacion(Base):
    __tablename__ = "estado_cotizacion"

    id_estado_cotizacion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)


class Cotizacion(Base):
    __tablename__ = "cotizacion"
    __table_args__ = (
        UniqueConstraint("id_incidente", "id_taller", name="uq_cotizacion_incidente_taller"),
    )

    id_cotizacion = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    id_estado_cotizacion = Column(Integer, ForeignKey("estado_cotizacion.id_estado_cotizacion"), nullable=False)

    monto_servicio = Column(Numeric(10, 2), nullable=True)
    monto_repuestos = Column(Numeric(10, 2), nullable=True, default=0)
    garantia_dias = Column(Integer, nullable=True)
    nota = Column(Text, nullable=True)
    validez_hasta = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    incidente = relationship("Incidente")
    taller = relationship("Taller")
    estado = relationship("EstadoCotizacion")

    @property
    def monto_total(self) -> float:
        s = self.monto_servicio or 0
        r = self.monto_repuestos or 0
        return float(s) + float(r)
