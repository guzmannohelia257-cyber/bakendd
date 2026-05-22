from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.sql import func

from app.db.session import Base


class UbicacionTecnico(Base):
    __tablename__ = "ubicacion_tecnico"

    id_ubicacion = Column(BigInteger, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    id_asignacion = Column(Integer, ForeignKey("asignacion.id_asignacion"), nullable=True, index=True)

    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    velocidad_kmh = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
