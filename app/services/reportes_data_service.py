"""
Capa de datos del asistente de reportes (admin rol 4).

Define un CATALOGO cerrado de reportes predefinidos. Cada report_id mapea a una
funcion que reutiliza los servicios existentes (kpi_service y la logica de
ganancias de api/admin.py) y devuelve una forma tabular uniforme
(titulo, columnas, filas) lista para pintar en tabla o exportar a PDF/Excel.

No se genera SQL libre: el NL service solo puede elegir un report_id de este
catalogo. Toda ejecucion corre con current_tenant.set(0) (super-admin ve TODO,
incluido el flujo publico con id_tenant NULL), igual que los endpoints de KPIs.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.core.tenant_context import current_tenant
from app.models.catalogos import EstadoPago
from app.models.taller import Taller
from app.models.transaccional import Pago
from app.schemas.reportes_schema import ReporteParams
from app.services import kpi_service
# Reutilizamos los helpers de ganancias ya probados, sin duplicar su SQL ni
# tocar api/admin.py (sus endpoints quedan intactos).
from app.api.admin import MONTH_NAMES, _eval_map, _subq_asig_completada


# Helpers de fechas / parametros

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _rango(p: ReporteParams):
    """Resuelve (desde, hasta). Default: ultimos 30 dias (kpi_service)."""
    desde = _parse_iso(p.desde)
    hasta = _parse_iso(p.hasta)
    if desde is None or hasta is None:
        d_def, h_def = kpi_service._rango_default()
        desde = desde or d_def
        hasta = hasta or h_def
    return desde, hasta


def _sla(p: ReporteParams) -> int:
    return p.sla_minutos or kpi_service.SLA_MINUTOS_DEFAULT


def _limite(p: ReporteParams, default: int = 10) -> int:
    return p.limite or default


# Reverse-geocoding de zonas (lat/lng -> calle/barrio) con Nominatim (OSM).
# Cache en memoria por celda redondeada; respeta el limite de 1 req/seg de
# Nominatim. Si falla o no resuelve, cae a las coordenadas como etiqueta.
_GEOCACHE: dict = {}
_NOMINATIM_UA = "Yary2-Reportes/1.0 (asistencia vial)"
_geo_ultimo = [0.0]


def _geo_throttle() -> None:
    ahora = time.monotonic()
    delta = ahora - _geo_ultimo[0]
    if delta < 1.1:
        time.sleep(1.1 - delta)
    _geo_ultimo[0] = time.monotonic()


def _reverse_geocode(lat, lng) -> str:
    key = (round(float(lat), 4), round(float(lng), 4))
    if key in _GEOCACHE:
        return _GEOCACHE[key]

    etiqueta = ""
    try:
        _geo_throttle()
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 17, "addressdetails": 1},
            headers={"User-Agent": _NOMINATIM_UA, "Accept": "application/json"},
            timeout=8,
        )
        if resp.status_code == 200:
            j = resp.json() or {}
            a = j.get("address") or {}
            partes = [
                a.get("road") or a.get("pedestrian") or a.get("neighbourhood"),
                a.get("suburb") or a.get("city_district") or a.get("city") or a.get("town") or a.get("village"),
            ]
            etiqueta = ", ".join([p for p in partes if p])
            if not etiqueta:
                etiqueta = ", ".join((j.get("display_name") or "").split(",")[:2]).strip()
    except Exception:
        etiqueta = ""

    if not etiqueta:
        etiqueta = f"{round(float(lat), 5)}, {round(float(lng), 5)}"
    _GEOCACHE[key] = etiqueta
    return etiqueta


# Reportes basados en kpi_service

def _r_incidentes_por_taller(db, p):
    desde, hasta = _rango(p)
    rows = kpi_service.kpis_por_taller(db, desde, hasta, sla_minutos=_sla(p))
    columnas = ["Taller", "Tiempo asignación (min)", "Tiempo llegada (min)",
                "Total incidentes", "Cancelados", "SLA %", "Completadas"]
    filas = [{
        "Taller": r["nombre"],
        "Tiempo asignación (min)": r["tiempo_asignacion_min"],
        "Tiempo llegada (min)": r["tiempo_llegada_min"],
        "Total incidentes": r["total_incidentes"],
        "Cancelados": r["casos_cancelados"],
        "SLA %": r["sla_porcentaje"],
        "Completadas": r["completadas"],
    } for r in rows]
    return "Incidentes y desempeño por taller", columnas, filas


def _r_zonas(db, p):
    desde, hasta = _rango(p)
    rows = kpi_service.zonas_mas_incidentes(db, desde, hasta, p.id_tenant, limite=_limite(p))
    columnas = ["Zona", "Total incidentes"]
    filas = [
        {"Zona": _reverse_geocode(r["lat"], r["lng"]), "Total incidentes": r["total"]}
        for r in rows
    ]
    return "Zonas con más incidentes", columnas, filas


def _r_sla(db, p):
    desde, hasta = _rango(p)
    d = kpi_service.cumplimiento_sla(db, desde, hasta, p.id_tenant, sla_minutos=_sla(p))
    columnas = ["Total completadas", "Cumplen SLA", "Porcentaje %", "Umbral SLA (min)"]
    filas = [{
        "Total completadas": d["total_completadas"],
        "Cumplen SLA": d["cumplen_sla"],
        "Porcentaje %": d["porcentaje"],
        "Umbral SLA (min)": d["sla_minutos"],
    }]
    return "Cumplimiento de SLA", columnas, filas


def _r_resumen(db, p):
    desde, hasta = _rango(p)
    r = kpi_service.resumen_completo(db, desde, hasta, p.id_tenant, sla_minutos=_sla(p))
    sla = r.get("sla_cumplimiento") or {}
    columnas = ["Métrica", "Valor"]
    filas = [
        {"Métrica": "Total incidentes", "Valor": r["total_incidentes"]},
        {"Métrica": "Casos cancelados", "Valor": r["casos_cancelados"]},
        {"Métrica": "Tiempo promedio de asignación (min)", "Valor": r["tiempo_promedio_asignacion_min"]},
        {"Métrica": "Tiempo promedio de llegada (min)", "Valor": r["tiempo_promedio_llegada_min"]},
        {"Métrica": "Cumplimiento SLA (%)", "Valor": sla.get("porcentaje", 0)},
        {"Métrica": "Servicios completados (SLA)", "Valor": sla.get("total_completadas", 0)},
    ]
    return "Resumen general del periodo", columnas, filas


def _r_categorias(db, p):
    desde, hasta = _rango(p)
    rows = kpi_service.incidentes_por_categoria(db, desde, hasta, p.id_tenant)
    columnas = ["Código", "Categoría", "Total"]
    filas = [{"Código": r["codigo"], "Categoría": r["nombre"], "Total": r["total"]} for r in rows]
    return "Incidentes por categoría", columnas, filas


def _r_ranking(db, p):
    desde, hasta = _rango(p)
    rows = kpi_service.ranking_talleres(db, desde, hasta, limite=_limite(p))
    columnas = ["Taller", "Rating", "Completadas", "Tasa aceptación", "Score"]
    filas = [{
        "Taller": r["nombre"],
        "Rating": r["rating_promedio"],
        "Completadas": r["completadas"],
        "Tasa aceptación": r["tasa_aceptacion"],
        "Score": r["score"],
    } for r in rows]
    return "Ranking de talleres", columnas, filas


def _r_total_incidentes(db, p):
    desde, hasta = _rango(p)
    n = kpi_service.total_incidentes(db, desde, hasta, p.id_tenant)
    return "Total de incidentes del periodo", ["Total incidentes"], [{"Total incidentes": n}]


def _r_cancelados(db, p):
    desde, hasta = _rango(p)
    n = kpi_service.incidentes_cancelados(db, desde, hasta, p.id_tenant)
    return "Incidentes cancelados del periodo", ["Incidentes cancelados"], [{"Incidentes cancelados": n}]


def _r_tiempo_asignacion(db, p):
    desde, hasta = _rango(p)
    v = round(kpi_service.tiempo_promedio_asignacion_min(db, desde, hasta, p.id_tenant), 2)
    return ("Tiempo promedio de asignación",
            ["Tiempo promedio de asignación (min)"],
            [{"Tiempo promedio de asignación (min)": v}])


def _r_tiempo_llegada(db, p):
    desde, hasta = _rango(p)
    v = round(kpi_service.tiempo_promedio_llegada_min(db, desde, hasta, p.id_tenant), 2)
    return ("Tiempo promedio de llegada",
            ["Tiempo promedio de llegada (min)"],
            [{"Tiempo promedio de llegada (min)": v}])


# Reportes de ganancias (reusan helpers de api/admin.py)

def _r_ganancias_mensuales(db, p):
    q = (
        db.query(
            extract("year", Pago.created_at).label("anio"),
            extract("month", Pago.created_at).label("mes"),
            func.count(Pago.id_pago).label("total_pagos"),
            func.coalesce(func.sum(Pago.monto_total), 0).label("monto_total"),
            func.coalesce(func.sum(Pago.comision_plataforma), 0).label("comision"),
        )
        .join(EstadoPago, EstadoPago.id_estado_pago == Pago.id_estado_pago)
        .filter(EstadoPago.nombre == "completado")
    )
    if p.anio:
        q = q.filter(extract("year", Pago.created_at) == p.anio)
    rows = (
        q.group_by(extract("year", Pago.created_at), extract("month", Pago.created_at))
        .order_by(extract("year", Pago.created_at).desc(), extract("month", Pago.created_at).desc())
        .all()
    )
    columnas = ["Año", "Mes", "Pagos", "Monto procesado (Bs)", "Comisión (Bs)"]
    filas = [{
        "Año": int(r.anio),
        "Mes": MONTH_NAMES.get(int(r.mes), str(int(r.mes))),
        "Pagos": int(r.total_pagos),
        "Monto procesado (Bs)": round(float(r.monto_total), 2),
        "Comisión (Bs)": round(float(r.comision), 2),
    } for r in rows]
    return "Ganancias mensuales de la plataforma", columnas, filas


def _r_ganancias_por_taller(db, p):
    sub = _subq_asig_completada(db)
    q = (
        db.query(
            Taller.id_taller,
            Taller.nombre,
            Taller.email,
            func.count(Pago.id_pago).label("total_pagos"),
            func.coalesce(func.sum(Pago.monto_total), 0).label("monto_total"),
            func.coalesce(func.sum(Pago.comision_plataforma), 0).label("comision"),
        )
        .select_from(Taller)
        .join(sub, sub.c.id_taller == Taller.id_taller)
        .join(Pago, Pago.id_incidente == sub.c.id_incidente)
        .join(EstadoPago, EstadoPago.id_estado_pago == Pago.id_estado_pago)
        .filter(EstadoPago.nombre == "completado")
    )
    if p.anio:
        q = q.filter(extract("year", Pago.created_at) == p.anio)
    if p.mes:
        q = q.filter(extract("month", Pago.created_at) == p.mes)
    rows = (
        q.group_by(Taller.id_taller, Taller.nombre, Taller.email)
        .order_by(func.sum(Pago.comision_plataforma).desc())
        .all()
    )
    evals = _eval_map(db)
    columnas = ["Taller", "Email", "Pagos", "Monto (Bs)", "Comisión (Bs)", "Rating", "Evaluaciones"]
    filas = []
    for r in rows:
        tiene_rating = r.id_taller in evals and evals[r.id_taller][0]
        filas.append({
            "Taller": r.nombre,
            "Email": r.email,
            "Pagos": int(r.total_pagos),
            "Monto (Bs)": round(float(r.monto_total), 2),
            "Comisión (Bs)": round(float(r.comision), 2),
            "Rating": round(float(evals[r.id_taller][0]), 2) if tiene_rating else "—",
            "Evaluaciones": evals[r.id_taller][1] if r.id_taller in evals else 0,
        })
    return "Ganancias por taller", columnas, filas


# Catalogo cerrado de reportes

CATALOGO = [
    {"report_id": "incidentes_por_taller", "titulo": "Incidentes por taller",
     "descripcion": "Desempeño de cada taller: incidentes, tiempos, cancelados y SLA.",
     "params": ["desde", "hasta", "sla_minutos"],
     "ejemplos": ["incidentes del último mes por taller", "comparativa de talleres"]},
    {"report_id": "zonas_mas_averias", "titulo": "Zonas con más averías",
     "descripcion": "Zonas geográficas con mayor número de incidentes.",
     "params": ["desde", "hasta", "limite", "id_tenant"],
     "ejemplos": ["zonas con más averías en mayo", "dónde hay más incidentes"]},
    {"report_id": "sla_cumplimiento", "titulo": "Cumplimiento de SLA",
     "descripcion": "Porcentaje de servicios completados dentro del umbral de SLA.",
     "params": ["desde", "hasta", "id_tenant", "sla_minutos"],
     "ejemplos": ["cumplimiento de SLA del periodo", "qué tan rápido se atiende"]},
    {"report_id": "resumen_general", "titulo": "Resumen general",
     "descripcion": "Resumen consolidado de KPIs del periodo.",
     "params": ["desde", "hasta", "id_tenant", "sla_minutos"],
     "ejemplos": ["resumen general", "panorama del mes"]},
    {"report_id": "incidentes_por_categoria", "titulo": "Incidentes por categoría",
     "descripcion": "Conteo de incidentes agrupado por tipo de avería.",
     "params": ["desde", "hasta", "id_tenant"],
     "ejemplos": ["incidentes por tipo de avería", "qué fallas son más comunes"]},
    {"report_id": "ranking_talleres", "titulo": "Ranking de talleres",
     "descripcion": "Mejores talleres por rating, aceptación y volumen.",
     "params": ["desde", "hasta", "limite"],
     "ejemplos": ["mejores talleres", "ranking de talleres"]},
    {"report_id": "total_incidentes", "titulo": "Total de incidentes",
     "descripcion": "Cantidad total de incidentes creados en el periodo.",
     "params": ["desde", "hasta", "id_tenant"],
     "ejemplos": ["cuántos incidentes hubo", "total de incidentes"]},
    {"report_id": "incidentes_cancelados", "titulo": "Incidentes cancelados",
     "descripcion": "Cantidad de incidentes cancelados en el periodo.",
     "params": ["desde", "hasta", "id_tenant"],
     "ejemplos": ["cancelaciones del periodo", "cuántos se cancelaron"]},
    {"report_id": "tiempo_asignacion", "titulo": "Tiempo de asignación",
     "descripcion": "Tiempo promedio desde el reporte hasta que un taller acepta.",
     "params": ["desde", "hasta", "id_tenant"],
     "ejemplos": ["tiempo promedio de asignación"]},
    {"report_id": "tiempo_llegada", "titulo": "Tiempo de llegada",
     "descripcion": "Tiempo promedio desde la aceptación hasta la llegada.",
     "params": ["desde", "hasta", "id_tenant"],
     "ejemplos": ["tiempo promedio de llegada"]},
    {"report_id": "ganancias_mensuales", "titulo": "Ganancias mensuales",
     "descripcion": "Comisión y montos procesados por la plataforma, por mes.",
     "params": ["anio"],
     "ejemplos": ["ganancias por mes", "comisiones de este año"]},
    {"report_id": "ganancias_por_taller", "titulo": "Ganancias por taller",
     "descripcion": "Comisión y montos generados por cada taller.",
     "params": ["anio", "mes"],
     "ejemplos": ["ganancias por taller", "qué taller genera más comisión"]},
]

_EXECUTORS = {
    "incidentes_por_taller": _r_incidentes_por_taller,
    "zonas_mas_averias": _r_zonas,
    "sla_cumplimiento": _r_sla,
    "resumen_general": _r_resumen,
    "incidentes_por_categoria": _r_categorias,
    "ranking_talleres": _r_ranking,
    "total_incidentes": _r_total_incidentes,
    "incidentes_cancelados": _r_cancelados,
    "tiempo_asignacion": _r_tiempo_asignacion,
    "tiempo_llegada": _r_tiempo_llegada,
    "ganancias_mensuales": _r_ganancias_mensuales,
    "ganancias_por_taller": _r_ganancias_por_taller,
}


def ids_validos() -> set:
    return set(_EXECUTORS.keys())


def ejecutar(db: Session, report_id: str, params: ReporteParams):
    """Ejecuta un reporte del catalogo y devuelve (titulo, columnas, filas).

    Corre con current_tenant.set(0) para que el super-admin consolide TODOS los
    talleres e incluya el flujo publico (id_tenant NULL). Lanza KeyError si el
    report_id no esta en el catalogo.
    """
    fn = _EXECUTORS.get(report_id)
    if fn is None:
        raise KeyError(report_id)
    tok = current_tenant.set(0)
    try:
        return fn(db, params)
    finally:
        current_tenant.reset(tok)
