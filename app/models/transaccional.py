"""
Notificaciones, pagos, métricas y mensajería.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Notificacion(Base):
    __tablename__ = "notificacion"
    __table_args__ = (
        CheckConstraint(
            "(id_usuario IS NOT NULL AND id_taller IS NULL) OR "
            "(id_usuario IS NULL AND id_taller IS NOT NULL)",
            name="chk_notif_destino",
        ),
    )

    id_notificacion = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=True)

    titulo = Column(String(100), nullable=False)
    mensaje = Column(Text, nullable=False)
    leido = Column(Boolean, default=False, nullable=False)
    enviado_push = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario = relationship("Usuario")
    taller = relationship("Taller")
    incidente = relationship("Incidente")


class Pago(Base):
    __tablename__ = "pago"

    id_pago = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False)
    id_metodo_pago = Column(Integer, ForeignKey("metodo_pago.id_metodo_pago"), nullable=False)
    id_estado_pago = Column(Integer, ForeignKey("estado_pago.id_estado_pago"), nullable=False)

    monto_total = Column(Numeric(10, 2), nullable=False)
    comision_plataforma = Column(Numeric(10, 2), nullable=False)
    monto_taller = Column(Numeric(10, 2), nullable=False)
    referencia_externa = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    incidente = relationship("Incidente")
    metodo = relationship("MetodoPago")
    estado = relationship("EstadoPago")


class Metrica(Base):
    __tablename__ = "metrica"

    id_metrica = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, unique=True)

    fecha_inicio = Column(DateTime(timezone=True), nullable=True)
    fecha_asignacion = Column(DateTime(timezone=True), nullable=True)
    fecha_llegada_tecnico = Column(DateTime(timezone=True), nullable=True)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)

    tiempo_respuesta_min = Column(Integer, nullable=True)
    tiempo_llegada_min = Column(Integer, nullable=True)
    tiempo_resolucion_min = Column(Integer, nullable=True)

    calificacion_cliente = Column(Integer, nullable=True)  # 1-5
    comentario_cliente = Column(Text, nullable=True)

    incidente = relationship("Incidente")


class Mensaje(Base):
    __tablename__ = "mensaje"
    __table_args__ = (
        CheckConstraint(
            "(id_usuario IS NOT NULL AND id_taller IS NULL) OR "
            "(id_usuario IS NULL AND id_taller IS NOT NULL)",
            name="chk_msg_origen",
        ),
    )

    id_mensaje = Column(Integer, primary_key=True, index=True)
    id_tenant = Column(Integer, ForeignKey("tenant.id_tenant"), nullable=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=True)

    contenido = Column(Text, nullable=False)
    leido = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incidente = relationship("Incidente")
    usuario = relationship("Usuario")
    taller = relationship("Taller")
