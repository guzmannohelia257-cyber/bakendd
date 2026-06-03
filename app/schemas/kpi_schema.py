from typing import Optional, List

from pydantic import BaseModel


class CategoriaCount(BaseModel):
    codigo: Optional[str]
    nombre: str
    total: int


class ZonaKpi(BaseModel):
    lat: float
    lng: float
    total: int


class SlaKpi(BaseModel):
    total_completadas: int
    cumplen_sla: int
    porcentaje: float
    sla_minutos: int


class KpiResumen(BaseModel):
    desde: str
    hasta: str
    tiempo_promedio_asignacion_min: float
    tiempo_promedio_llegada_min: float
    incidentes_por_categoria: List[CategoriaCount]
    casos_cancelados: int = 0
    total_incidentes: int = 0
    zonas_mas_incidentes: List[ZonaKpi] = []
    sla_cumplimiento: Optional[SlaKpi] = None


class TallerKpiRow(BaseModel):
    id_taller: int
    id_tenant: Optional[int] = None
    nombre: str
    tiempo_asignacion_min: float
    tiempo_llegada_min: float
    total_incidentes: int
    casos_cancelados: int
    sla_porcentaje: float
    completadas: int


class TallerRanking(BaseModel):
    id_taller: int
    nombre: str
    rating_promedio: float
    completadas: int
    tasa_aceptacion: float
    score: float
