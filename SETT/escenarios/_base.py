"""
Helpers reutilizables por todos los escenarios.

Centraliza la creacion de:
  - Incidente con historial coherente.
  - Metrica con timestamps acordes al estado.
  - Evidencias (texto + imagen).
  - Candidatos de asignacion (top-3 simulando motor).
  - Asignacion con historial de transiciones.
  - Mensaje cliente -> taller.
  - Notificaciones.
  - Cotizacion (opcional).
  - Pago + Evaluacion (opcional).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cotizacion import Cotizacion
from app.models.incidente import (
    Asignacion,
    CandidatoAsignacion,
    Evaluacion,
    Evidencia,
    HistorialEstadoAsignacion,
    HistorialEstadoIncidente,
    Incidente,
)
from app.models.transaccional import Mensaje, Metrica, Notificacion, Pago
from SETT.utils import Ctx, logger


# Cadenas de transicion validas para construir el historial del incidente
# y de la asignacion segun su estado final.
TRANSICIONES_INCIDENTE = {
    "pendiente":  [],
    "en_proceso": ["en_proceso"],
    "atendido":   ["en_proceso", "atendido"],
    "cancelado":  ["cancelado"],
}

TRANSICIONES_ASIGNACION = {
    "pendiente":  [],
    "aceptada":   ["aceptada"],
    "rechazada":  ["rechazada"],
    "en_camino":  ["aceptada", "en_camino"],
    "llegado":    ["aceptada", "en_camino", "llegado"],
    "completada": ["aceptada", "en_camino", "llegado", "completada"],
    "cancelada":  ["cancelada"],
}


@dataclass
class EscenarioInput:
    """Definicion declarativa de un escenario."""
    cliente_key: str
    taller_idx: int
    descripcion: str
    categoria: str
    prioridad: str
    estado_incidente: str
    estado_asignacion: str
    lat: float
    lng: float

    tecnico_idx: Optional[int] = None
    nota_taller: Optional[str] = None
    motivo_cancelacion: Optional[str] = None
    cancelada_por: Optional[str] = None  # "cliente" | "taller" | "sistema"

    # Cotizacion (opcional)
    cotizacion_estado: Optional[str] = None  # pendiente / enviada / aceptada / rechazada / expirada
    cotizacion_monto: float = 120.00

    # Pago + evaluacion (opcional)
    pago_estado: Optional[str] = None        # pendiente / procesando / completado / fallido / reembolsado
    pago_monto: float = 95.00
    pago_metodo: str = "tarjeta"
    evaluacion_estrellas: Optional[int] = None
    evaluacion_comentario: Optional[str] = None

    # Cliente sin tenant: se hereda del taller asignado
    tenant_del_taller: bool = True


@dataclass
class EscenarioResultado:
    incidente: Incidente
    asignacion: Optional[Asignacion]
    evidencias: list[Evidencia] = field(default_factory=list)
    cotizacion: Optional[Cotizacion] = None
    pago: Optional[Pago] = None
    evaluacion: Optional[Evaluacion] = None


def crear_escenario(db: Session, ctx: Ctx, e: EscenarioInput) -> EscenarioResultado:
    """Crea TODO el grafo de objetos para un escenario."""
    cliente = ctx.clientes[e.cliente_key]
    vehiculo = ctx.vehiculos[e.cliente_key]
    taller = ctx.talleres[e.taller_idx]
    tecnico = ctx.tecnicos[e.tecnico_idx] if e.tecnico_idx is not None else None
    id_tenant = taller.id_tenant if e.tenant_del_taller else None

    ahora = datetime.now(timezone.utc)
    delta_horas = ctx.escenarios_creados + 1
    fecha_inicio = ahora - timedelta(hours=delta_horas)

    # ── Incidente ──────────────────────────────────────────────────────────
    incidente = Incidente(
        id_tenant=id_tenant,
        id_usuario=cliente.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=ctx.estado_incidente[e.estado_incidente].id_estado,
        id_categoria=ctx.categoria[e.categoria].id_categoria,
        id_prioridad=ctx.prioridad[e.prioridad].id_prioridad,
        latitud=e.lat,
        longitud=e.lng,
        descripcion_usuario=e.descripcion,
        resumen_ia=f"[SETT] Clasificacion automatica: {e.categoria} ({e.prioridad})",
        clasificacion_ia_confianza=0.92,
        requiere_revision_manual=False,
    )
    db.add(incidente)
    db.flush()

    # ── Historial incidente: pendiente -> ... -> estado_final ──────────────
    db.add(HistorialEstadoIncidente(
        id_incidente=incidente.id_incidente,
        id_estado_anterior=None,
        id_estado_nuevo=ctx.estado_incidente["pendiente"].id_estado,
        observacion="Incidente reportado",
    ))
    prev_inc = "pendiente"
    for siguiente in TRANSICIONES_INCIDENTE[e.estado_incidente]:
        db.add(HistorialEstadoIncidente(
            id_incidente=incidente.id_incidente,
            id_estado_anterior=ctx.estado_incidente[prev_inc].id_estado,
            id_estado_nuevo=ctx.estado_incidente[siguiente].id_estado,
            observacion=f"Transicion a {siguiente}",
        ))
        prev_inc = siguiente

    # ── Metrica con timestamps consistentes con el estado ─────────────────
    metrica = Metrica(
        id_tenant=id_tenant,
        id_incidente=incidente.id_incidente,
        fecha_inicio=fecha_inicio,
    )
    if e.estado_asignacion in ("aceptada", "en_camino", "llegado", "completada"):
        metrica.fecha_asignacion = fecha_inicio + timedelta(minutes=5)
        metrica.tiempo_respuesta_min = 5
    if e.estado_asignacion in ("en_camino", "llegado", "completada"):
        metrica.fecha_llegada_tecnico = fecha_inicio + timedelta(minutes=20)
        metrica.tiempo_llegada_min = 15
    if e.estado_asignacion == "completada":
        metrica.fecha_fin = fecha_inicio + timedelta(minutes=60)
        metrica.tiempo_resolucion_min = 60
        if e.evaluacion_estrellas:
            metrica.calificacion_cliente = e.evaluacion_estrellas
            metrica.comentario_cliente = e.evaluacion_comentario or ""
    db.add(metrica)

    # ── Evidencias placeholder ─────────────────────────────────────────────
    ev_texto = Evidencia(
        id_tenant=id_tenant,
        id_incidente=incidente.id_incidente,
        id_tipo_evidencia=ctx.tipo_evidencia["texto"].id_tipo_evidencia,
        url_archivo="https://placehold.co/seed-nota.txt",
        descripcion_ia="Nota de texto del cliente",
    )
    ev_imagen = Evidencia(
        id_tenant=id_tenant,
        id_incidente=incidente.id_incidente,
        id_tipo_evidencia=ctx.tipo_evidencia["imagen"].id_tipo_evidencia,
        url_archivo="https://placehold.co/600x400/png?text=Evidencia",
        descripcion_ia="Foto del incidente",
    )
    db.add_all([ev_texto, ev_imagen])

    # ── Candidatos (top 3) ─────────────────────────────────────────────────
    db.add(CandidatoAsignacion(
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        distancia_km=1.8,
        score_total=92.0,
        seleccionado=True,
    ))
    otros = [t for t in ctx.talleres if t.id_taller != taller.id_taller]
    for j, otro in enumerate(otros[:2]):
        db.add(CandidatoAsignacion(
            id_incidente=incidente.id_incidente,
            id_taller=otro.id_taller,
            distancia_km=3.0 + j,
            score_total=72.0 - j * 4,
            seleccionado=False,
        ))

    # ── Asignacion ─────────────────────────────────────────────────────────
    # Importante: cuando estado_asignacion == 'pendiente' NO creamos fila en
    # `asignacion`: en la realidad la asignacion solo se materializa cuando un
    # taller acepta. Mientras tanto solo existen los `candidato_asignacion`.
    # Esto evita que en el historial del cliente aparezcan acciones (Mensajes,
    # Ver tecnico, etc.) cuando todavia ningun taller confirmo.
    asignacion: Optional[Asignacion] = None
    if e.estado_asignacion != "pendiente":
        asignacion = Asignacion(
            id_tenant=id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_usuario=tecnico.id_usuario if tecnico else None,
            id_estado_asignacion=ctx.estado_asignacion[e.estado_asignacion].id_estado_asignacion,
            eta_minutos=20,
            costo_estimado=e.pago_monto if e.estado_asignacion == "completada" else None,
            nota_taller=e.nota_taller,
            cancelada_at=ahora if e.estado_asignacion == "cancelada" else None,
            motivo_cancelacion=e.motivo_cancelacion,
            cancelada_por=e.cancelada_por,
        )
        db.add(asignacion)
        db.flush()

        # ── Historial asignacion: pendiente -> ... -> estado_final ─────────
        db.add(HistorialEstadoAsignacion(
            id_asignacion=asignacion.id_asignacion,
            id_estado_anterior=None,
            id_estado_nuevo=ctx.estado_asignacion["pendiente"].id_estado_asignacion,
            observacion=f"Motor selecciono {taller.nombre}",
        ))
        prev_asig = "pendiente"
        for siguiente in TRANSICIONES_ASIGNACION[e.estado_asignacion]:
            db.add(HistorialEstadoAsignacion(
                id_asignacion=asignacion.id_asignacion,
                id_estado_anterior=ctx.estado_asignacion[prev_asig].id_estado_asignacion,
                id_estado_nuevo=ctx.estado_asignacion[siguiente].id_estado_asignacion,
                observacion=f"Transicion a {siguiente}",
            ))
            prev_asig = siguiente

    # ── Cotizacion (opcional) ──────────────────────────────────────────────
    cotizacion = None
    if e.cotizacion_estado:
        validez = ahora + timedelta(days=3)
        if e.cotizacion_estado == "expirada":
            validez = ahora - timedelta(days=1)
        cotizacion = Cotizacion(
            id_tenant=taller.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_estado_cotizacion=ctx.estado_cotizacion[e.cotizacion_estado].id_estado_cotizacion,
            monto_servicio=e.cotizacion_monto,
            monto_repuestos=20.00,
            garantia_dias=15,
            nota=f"Cotizacion {e.cotizacion_estado} (SETT)",
            validez_hasta=validez,
        )
        db.add(cotizacion)

    # ── Pago + Evaluacion (opcional) ───────────────────────────────────────
    pago = None
    evaluacion = None
    if e.pago_estado:
        pago = Pago(
            id_tenant=id_tenant,
            id_incidente=incidente.id_incidente,
            id_metodo_pago=ctx.metodo_pago[e.pago_metodo].id_metodo_pago,
            id_estado_pago=ctx.estado_pago[e.pago_estado].id_estado_pago,
            monto_total=e.pago_monto,
            comision_plataforma=round(e.pago_monto * 0.10, 2),
            monto_taller=round(e.pago_monto * 0.90, 2),
            referencia_externa=f"pi_sett_{incidente.id_incidente}",
        )
        db.add(pago)

    if e.evaluacion_estrellas:
        evaluacion = Evaluacion(
            id_tenant=id_tenant,
            id_incidente=incidente.id_incidente,
            id_usuario=cliente.id_usuario,
            id_taller=taller.id_taller,
            estrellas=e.evaluacion_estrellas,
            comentario=e.evaluacion_comentario or "Excelente servicio",
        )
        db.add(evaluacion)

    # ── Mensajes ───────────────────────────────────────────────────────────
    db.add(Mensaje(
        id_tenant=id_tenant,
        id_incidente=incidente.id_incidente,
        id_usuario=cliente.id_usuario,
        contenido=f"Hola, necesito ayuda: {e.descripcion}",
        leido=True,
    ))
    if e.estado_asignacion not in ("pendiente",):
        db.add(Mensaje(
            id_tenant=id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            contenido="Recibida la solicitud. Tecnico en marcha.",
            leido=False,
        ))

    # ── Notificaciones ─────────────────────────────────────────────────────
    db.add(Notificacion(
        id_tenant=id_tenant,
        id_taller=taller.id_taller,
        id_incidente=incidente.id_incidente,
        titulo="Nueva solicitud de asistencia",
        mensaje=f"Solicitud de {cliente.nombre} ({e.categoria})",
        leido=e.estado_asignacion not in ("pendiente",),
    ))
    if e.estado_asignacion in ("aceptada", "en_camino", "llegado", "completada"):
        db.add(Notificacion(
            id_tenant=id_tenant,
            id_usuario=cliente.id_usuario,
            id_incidente=incidente.id_incidente,
            titulo="Solicitud aceptada",
            mensaje=f"{taller.nombre} acepto tu solicitud",
            leido=e.estado_asignacion == "completada",
        ))

    db.commit()
    db.refresh(incidente)
    if asignacion is not None:
        db.refresh(asignacion)

    ctx.escenarios_creados += 1
    logger.info(
        f"[escenarios] #{ctx.escenarios_creados:02d} "
        f"cli={e.cliente_key:24s} inc={e.estado_incidente:10s} "
        f"asig={e.estado_asignacion:10s} cat={e.categoria}"
    )

    return EscenarioResultado(
        incidente=incidente,
        asignacion=asignacion,
        evidencias=[ev_texto, ev_imagen],
        cotizacion=cotizacion,
        pago=pago,
        evaluacion=evaluacion,
    )
