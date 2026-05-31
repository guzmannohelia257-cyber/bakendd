"""
Datos historicos (~3 meses) para poblar los KPIs, sobre todo de AutoRescate
(taller idx 0).

Crea incidentes distribuidos en los ultimos 90 dias con su asignacion,
historial de estados, metrica, evaluacion y pago. Las fechas created_at /
updated_at se fijan EXPLICITAMENTE en el pasado, porque los KPIs filtran por
esas columnas (no por la Metrica); de lo contrario todo quedaria "hoy" y los
KPIs por rango temporal saldrian vacios.

Es defensivo: run_all lo invoca dentro de un try/except, asi que si algo falla
NO rompe el seed base ni el arranque del servidor.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.incidente import (
    Asignacion,
    Evaluacion,
    HistorialEstadoAsignacion,
    HistorialEstadoIncidente,
    Incidente,
)
from app.models.transaccional import Metrica, Pago
from SETT.config import TECNICOS
from SETT.utils import Ctx, logger


DIAS_HISTORIA = 90
INCIDENTES_POR_DIA_MIN = 2
INCIDENTES_POR_DIA_MAX = 4

# Centro de Santa Cruz para dispersar lat/lng.
LAT0, LNG0 = -17.802, -63.190


def run(db: Session, ctx: Ctx) -> None:
    random.seed(20260531)  # determinista entre corridas

    pares = [(ctx.clientes[k], ctx.vehiculos[k]) for k in ctx.clientes if k in ctx.vehiculos]
    if not pares or not ctx.talleres:
        logger.info("[historico] sin clientes o talleres; se omite")
        return

    cat_keys = list(ctx.categoria.keys())
    prio_keys = list(ctx.prioridad.keys())
    if not cat_keys or not prio_keys:
        logger.info("[historico] sin categorias o prioridades; se omite")
        return

    # IDs de estados/catalogos (por nombre, como en el resto del SETT).
    def _ei(n):
        return ctx.estado_incidente[n].id_estado

    def _ea(n):
        return ctx.estado_asignacion[n].id_estado_asignacion

    estado_pago_completado = ctx.estado_pago.get("completado")
    metodo_tarjeta = ctx.metodo_pago.get("tarjeta")

    # Tecnicos por taller (segun la config: cada tecnico declara su taller_idx).
    tecnicos_por_taller: dict[int, list] = {}
    for j, tdef in enumerate(TECNICOS):
        if j < len(ctx.tecnicos):
            tecnicos_por_taller.setdefault(tdef["taller_idx"], []).append(ctx.tecnicos[j])

    # AutoRescate (idx 0) recibe la mayoria del volumen.
    taller_idxs = list(range(len(ctx.talleres)))
    pesos = [6 if i == 0 else 2 for i in taller_idxs]

    ahora = datetime.now(timezone.utc)
    creados = 0

    for dia in range(DIAS_HISTORIA, 0, -1):
        base_dia = ahora - timedelta(days=dia)
        for _ in range(random.randint(INCIDENTES_POR_DIA_MIN, INCIDENTES_POR_DIA_MAX)):
            taller_idx = random.choices(taller_idxs, weights=pesos, k=1)[0]
            taller = ctx.talleres[taller_idx]
            tecs = tecnicos_por_taller.get(taller_idx, [])
            tecnico = random.choice(tecs) if tecs else None
            cliente, vehiculo = random.choice(pares)
            cat = ctx.categoria[random.choice(cat_keys)]
            prio = ctx.prioridad[random.choice(prio_keys)]

            t0 = base_dia.replace(
                hour=random.randint(7, 20),
                minute=random.randint(0, 59),
                second=0,
                microsecond=0,
            )

            r = random.random()
            resultado = "completada" if r < 0.80 else ("cancelada" if r < 0.92 else "pendiente")
            estado_inc = {
                "completada": "atendido",
                "cancelada": "cancelado",
                "pendiente": "pendiente",
            }[resultado]

            inc = Incidente(
                id_tenant=taller.id_tenant,
                id_usuario=cliente.id_usuario,
                id_vehiculo=vehiculo.id_vehiculo,
                id_estado=_ei(estado_inc),
                id_categoria=cat.id_categoria,
                id_prioridad=prio.id_prioridad,
                latitud=LAT0 + random.uniform(-0.05, 0.05),
                longitud=LNG0 + random.uniform(-0.05, 0.05),
                descripcion_usuario="[historico] solicitud de asistencia",
                resumen_ia="[historico] clasificacion automatica",
                clasificacion_ia_confianza=0.9,
                requiere_revision_manual=False,
                created_at=t0,
                updated_at=t0,
            )
            db.add(inc)
            db.flush()

            db.add(HistorialEstadoIncidente(
                id_incidente=inc.id_incidente,
                id_estado_anterior=None,
                id_estado_nuevo=_ei("pendiente"),
                observacion="Incidente reportado",
                created_at=t0,
            ))

            if resultado == "pendiente":
                creados += 1
                continue

            # Tiempos coherentes (en minutos desde t0).
            m_acept = random.randint(2, 8)
            m_llegada = m_acept + random.randint(8, 22)
            m_fin = m_llegada + random.randint(20, 75)
            t_acept = t0 + timedelta(minutes=m_acept)
            t_camino = t0 + timedelta(minutes=m_acept + 1)
            t_llegada = t0 + timedelta(minutes=m_llegada)
            t_fin = t0 + timedelta(minutes=m_fin)

            if resultado == "cancelada":
                db.add(HistorialEstadoIncidente(
                    id_incidente=inc.id_incidente,
                    id_estado_anterior=_ei("pendiente"),
                    id_estado_nuevo=_ei("cancelado"),
                    observacion="Cancelado por el cliente",
                    created_at=t_acept,
                ))
                asig = Asignacion(
                    id_tenant=taller.id_tenant,
                    id_incidente=inc.id_incidente,
                    id_taller=taller.id_taller,
                    id_usuario=(tecnico.id_usuario if tecnico else None),
                    id_estado_asignacion=_ea("cancelada"),
                    eta_minutos=20,
                    cancelada_at=t_acept,
                    motivo_cancelacion="Cliente cancelo",
                    cancelada_por="cliente",
                    created_at=t0,
                    updated_at=t_acept,
                )
                db.add(asig)
                db.flush()
                db.add(HistorialEstadoAsignacion(
                    id_asignacion=asig.id_asignacion, id_estado_anterior=None,
                    id_estado_nuevo=_ea("pendiente"), observacion="Motor selecciono taller", created_at=t0,
                ))
                db.add(HistorialEstadoAsignacion(
                    id_asignacion=asig.id_asignacion, id_estado_anterior=_ea("pendiente"),
                    id_estado_nuevo=_ea("cancelada"), observacion="Cancelada", created_at=t_acept,
                ))
                db.add(Metrica(
                    id_tenant=taller.id_tenant, id_incidente=inc.id_incidente, fecha_inicio=t0,
                ))
                creados += 1
                continue

            # Completada.
            db.add(HistorialEstadoIncidente(
                id_incidente=inc.id_incidente, id_estado_anterior=_ei("pendiente"),
                id_estado_nuevo=_ei("en_proceso"), observacion="En proceso", created_at=t_acept,
            ))
            db.add(HistorialEstadoIncidente(
                id_incidente=inc.id_incidente, id_estado_anterior=_ei("en_proceso"),
                id_estado_nuevo=_ei("atendido"), observacion="Atendido", created_at=t_fin,
            ))

            monto = round(random.uniform(60, 350), 2)
            asig = Asignacion(
                id_tenant=taller.id_tenant,
                id_incidente=inc.id_incidente,
                id_taller=taller.id_taller,
                id_usuario=(tecnico.id_usuario if tecnico else None),
                id_estado_asignacion=_ea("completada"),
                eta_minutos=m_llegada,
                costo_estimado=monto,
                created_at=t_acept,
                updated_at=t_fin,
            )
            db.add(asig)
            db.flush()

            for prev, nuevo, obs, ts in [
                (None, "pendiente", "Motor selecciono taller", t0),
                ("pendiente", "aceptada", "Aceptada por el taller", t_acept),
                ("aceptada", "en_camino", "Tecnico en camino", t_camino),
                ("en_camino", "llegado", "Tecnico llego", t_llegada),
                ("llegado", "completada", "Servicio completado", t_fin),
            ]:
                db.add(HistorialEstadoAsignacion(
                    id_asignacion=asig.id_asignacion,
                    id_estado_anterior=(_ea(prev) if prev else None),
                    id_estado_nuevo=_ea(nuevo),
                    observacion=obs,
                    created_at=ts,
                ))

            db.add(Metrica(
                id_tenant=taller.id_tenant,
                id_incidente=inc.id_incidente,
                fecha_inicio=t0,
                fecha_asignacion=t_acept,
                fecha_llegada_tecnico=t_llegada,
                fecha_fin=t_fin,
                tiempo_respuesta_min=m_acept,
                tiempo_llegada_min=m_llegada - m_acept,
                tiempo_resolucion_min=m_fin,
            ))

            if estado_pago_completado is not None and metodo_tarjeta is not None:
                db.add(Pago(
                    id_tenant=taller.id_tenant,
                    id_incidente=inc.id_incidente,
                    id_metodo_pago=metodo_tarjeta.id_metodo_pago,
                    id_estado_pago=estado_pago_completado.id_estado_pago,
                    monto_total=monto,
                    comision_plataforma=round(monto * 0.10, 2),
                    monto_taller=round(monto * 0.90, 2),
                    referencia_externa=f"pi_hist_{inc.id_incidente}",
                    created_at=t_fin,
                    updated_at=t_fin,
                ))

            estrellas = random.choices([3, 4, 5], weights=[1, 3, 6], k=1)[0]
            db.add(Evaluacion(
                id_tenant=taller.id_tenant,
                id_incidente=inc.id_incidente,
                id_usuario=cliente.id_usuario,
                id_taller=taller.id_taller,
                estrellas=estrellas,
                comentario="Servicio historico",
                created_at=t_fin,
            ))
            creados += 1

        db.commit()  # un commit por dia para no acumular toda la historia en memoria

    logger.info(f"[historico] {creados} incidentes historicos creados (~{DIAS_HISTORIA} dias)")
