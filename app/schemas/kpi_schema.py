from typing import Optional, List

from pydantic import BaseModel


class CategoriaCount(BaseModel):
    codigo: Optional[str]
    nombre: str
    total: int


class KpiResumen(BaseModel):
    desde: str
    hasta: str
    tiempo_promedio_asignacion_min: float
    tiempo_promedio_llegada_min: float
    incidentes_por_categoria: List[CategoriaCount]


class TallerRanking(BaseModel):
    id_taller: int
    nombre: str
    rating_promedio: float
    completadas: int
    tasa_aceptacion: float
    score: float
