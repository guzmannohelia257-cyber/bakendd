"""
Encuentra talleres candidatos para un incidente.

Reglas:
  - Taller activo + disponible.
  - Taller declara la categoria del incidente.
  - Distancia <= radio_km.
  - Ordenado por distancia.
"""
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.models.incidente import CandidatoAsignacion, Incidente
from app.models.taller import Taller, TallerServicio


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


def buscar_talleres_compatibles(
    db: Session,
    incidente: Incidente,
    radio_km: float = 20.0,
    limite: int = 10,
) -> list[tuple[Taller, float]]:
    if incidente.id_categoria is None:
        return []

    rows = (
        db.query(Taller, TallerServicio)
        .join(TallerServicio, TallerServicio.id_taller == Taller.id_taller)
        .filter(
            TallerServicio.id_categoria == incidente.id_categoria,
            Taller.activo.is_(True),
            Taller.disponible.is_(True),
            Taller.latitud.isnot(None),
            Taller.longitud.isnot(None),
        )
        .all()
    )

    con_distancia = []
    for taller, _servicio in rows:
        d = _haversine_km(incidente.latitud, incidente.longitud, taller.latitud, taller.longitud)
        if d <= radio_km:
            con_distancia.append((taller, d))

    con_distancia.sort(key=lambda x: x[1])
    return con_distancia[:limite]


def crear_candidatos(
    db: Session, incidente: Incidente, talleres_dist: list[tuple[Taller, float]]
) -> list[CandidatoAsignacion]:
    candidatos = []
    for taller, dist in talleres_dist:
        cand = CandidatoAsignacion(
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            distancia_km=dist,
            score_total=None,
            seleccionado=False,
        )
        db.add(cand)
        candidatos.append(cand)
    db.commit()
    for c in candidatos:
        db.refresh(c)
    return candidatos
