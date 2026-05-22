"""
Servicio de tracking + ETA.

ETA usa OSRM publico por defecto. Si OSRM_URL en .env apunta a otra
instancia se usa esa. Si todo falla, fallback a calculo simple por
haversine / velocidad_promedio.
"""
from __future__ import annotations

import logging
import os
from math import asin, cos, radians, sin, sqrt

import httpx

logger = logging.getLogger(__name__)

OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
VELOCIDAD_DEFAULT_KMH = 40.0
GEOFENCE_RADIO_M = 100.0


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


async def calcular_eta(
    lat_origen: float,
    lng_origen: float,
    lat_destino: float,
    lng_destino: float,
) -> tuple[float, int]:
    """
    Devuelve (distancia_km, eta_segundos).
    """
    d_km = haversine_km(lat_origen, lng_origen, lat_destino, lng_destino)
    fallback_eta = int((d_km / VELOCIDAD_DEFAULT_KMH) * 3600)

    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{lng_origen},{lat_origen};{lng_destino},{lat_destino}?overview=false"
    )
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                return route["distance"] / 1000.0, int(route["duration"])
    except Exception as exc:
        logger.warning("OSRM fallo (%r). Usando fallback haversine.", exc)

    return d_km, fallback_eta


def llego_geofence(lat_tecnico: float, lng_tecnico: float, lat_inc: float, lng_inc: float) -> bool:
    d_km = haversine_km(lat_tecnico, lng_tecnico, lat_inc, lng_inc)
    return d_km * 1000 <= GEOFENCE_RADIO_M
