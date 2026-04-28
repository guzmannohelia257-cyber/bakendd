"""
Núcleo transaccional: incidentes, asignaciones, evidencias e historiales.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Incidente(Base):
    __tablename__ = "incidente"

    id_incidente = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculo.id_vehiculo"), nullable=False)
    id_estado = Column(Integer, ForeignKey("estado_incidente.id_estado"), nullable=False, index=True)
    id_categoria = Column(Integer, ForeignKey("categoria_problema.id_categoria"), nullable=True)
    id_prioridad = Column(Integer, ForeignKey("prioridad.id_prioridad"), nullable=True)

    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)

    descripcion_usuario = Column(Text, nullable=True)
    resumen_ia = Column(Text, nullable=True)
    clasificacion_ia_confianza = Column(Float, nullable=True)
    requiere_revision_manual = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="incidentes")
    vehiculo = relationship("Vehiculo", back_populates="incidentes")
    estado = relationship("EstadoIncidente")
    categoria = relationship("CategoriaProblema")
    prioridad = relationship("Prioridad")

    asignaciones = relationship("Asignacion", back_populates="incidente", cascade="all, delete-orphan")
    evidencias = relationship("Evidencia", back_populates="incidente", cascade="all, delete-orphan")
    historiales = relationship("HistorialEstadoIncidente", back_populates="incidente", cascade="all, delete-orphan")
    candidatos = relationship("CandidatoAsignacion", back_populates="incidente", cascade="all, delete-orphan")


class Asignacion(Base):
    __tablename__ = "asignacion"

    id_asignacion = Column(Integer, primary_key=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)  # Técnico (usuario con rol=3)
    id_estado_asignacion = Column(Integer, ForeignKey("estado_asignacion.id_estado_asignacion"), nullable=False)

    eta_minutos = Column(Integer, nullable=True)
    costo_estimado = Column(Numeric(10, 2), nullable=True)
    nota_taller = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    incidente = relationship("Incidente", back_populates="asignaciones")
    taller = relationship("Taller", back_populates="asignaciones")
    usuario_tecnico = relationship("Usuario", back_populates="asignaciones_tecnico")
    estado = relationship("EstadoAsignacion")
    historiales = relationship("HistorialEstadoAsignacion", back_populates="asignacion", cascade="all, delete-orphan")

    @property
    def costo_final(self):
        return self.costo_estimado


class Evidencia(Base):
    __tablename__ = "evidencia"

    id_evidencia = Column(Integer, primary_key=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, index=True)
    id_tipo_evidencia = Column(Integer, ForeignKey("tipo_evidencia.id_tipo_evidencia"), nullable=False)

    url_archivo = Column(String(500), nullable=False)
    transcripcion_audio = Column(Text, nullable=True)
    descripcion_ia = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incidente = relationship("Incidente", back_populates="evidencias")
    tipo = relationship("TipoEvidencia")


class HistorialEstadoIncidente(Base):
    __tablename__ = "historial_estado_incidente"

    id_historial = Column(Integer, primary_key=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False)
    id_estado_anterior = Column(Integer, ForeignKey("estado_incidente.id_estado"), nullable=True)
    id_estado_nuevo = Column(Integer, ForeignKey("estado_incidente.id_estado"), nullable=False)
    observacion = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incidente = relationship("Incidente", back_populates="historiales")
    estado_anterior = relationship("EstadoIncidente", foreign_keys=[id_estado_anterior])
    estado_nuevo = relationship("EstadoIncidente", foreign_keys=[id_estado_nuevo])


class HistorialEstadoAsignacion(Base):
    __tablename__ = "historial_estado_asignacion"

    id_historial = Column(Integer, primary_key=True, index=True)
    id_asignacion = Column(Integer, ForeignKey("asignacion.id_asignacion"), nullable=False)
    id_estado_anterior = Column(Integer, ForeignKey("estado_asignacion.id_estado_asignacion"), nullable=True)
    id_estado_nuevo = Column(Integer, ForeignKey("estado_asignacion.id_estado_asignacion"), nullable=False)
    observacion = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asignacion = relationship("Asignacion", back_populates="historiales")
    estado_anterior = relationship("EstadoAsignacion", foreign_keys=[id_estado_anterior])
    estado_nuevo = relationship("EstadoAsignacion", foreign_keys=[id_estado_nuevo])


class CandidatoAsignacion(Base):
    __tablename__ = "candidato_asignacion"

    id_candidato = Column(Integer, primary_key=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False)

    distancia_km = Column(Float, nullable=True)
    score_total = Column(Float, nullable=True)
    seleccionado = Column(Boolean, default=False, nullable=False)
    motivo_rechazo = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incidente = relationship("Incidente", back_populates="candidatos")
    taller = relationship("Taller")

    @property
    def rating_promedio(self):
        evaluaciones = getattr(self.taller, "evaluaciones", None)
        if not evaluaciones:
            return None

        total = sum(e.estrellas for e in evaluaciones if e.estrellas is not None)
        cantidad = sum(1 for e in evaluaciones if e.estrellas is not None)
        if cantidad == 0:
            return None

        return round(total / cantidad, 2)


class Evaluacion(Base):
    """
    Evaluación del servicio prestado.
    CU-10: Cliente califica al taller después de que se completa el incidente.
    """
    __tablename__ = "evaluacion"

    id_evaluacion = Column(Integer, primary_key=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), unique=True, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False)
    
    estrellas = Column(Integer, nullable=False)  # 1-5
    comentario = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incidente = relationship("Incidente")
    usuario = relationship("Usuario")
    taller = relationship("Taller", back_populates="evaluaciones")

    @property
    def id_tecnico(self):
        return None
