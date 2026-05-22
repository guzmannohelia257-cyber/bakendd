"""Endpoints de KPIs."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_taller, get_current_user
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.taller import Taller
from app.schemas.kpi_schema import KpiResumen, TallerRanking
from app.services import kpi_service


router = APIRouter(tags=["KPIs"])


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise HTTPException(400, f"Fecha invalida: {s}. Usar formato ISO-8601.")


@router.get(
    "/tenants/me/kpis",
    response_model=KpiResumen,
    summary="KPIs del tenant del taller autenticado",
)
def kpis_mi_tenant(
    desde: Optional[str] = Query(None, description="ISO date (default: hace 30 dias)"),
    hasta: Optional[str] = Query(None, description="ISO date (default: ahora)"),
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    if not current_taller.id_tenant:
        raise HTTPException(400, "Taller sin tenant")

    return kpi_service.resumen_completo(
        db=db,
        desde=_parse_iso(desde),
        hasta=_parse_iso(hasta),
        id_tenant=current_taller.id_tenant,
    )


@router.get(
    "/admin/kpis/ranking-talleres",
    response_model=List[TallerRanking],
    summary="Ranking global de talleres (super-admin)",
)
def ranking_global(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.id_rol != 4:
        raise HTTPException(403, "Requiere rol super-admin")

    d = _parse_iso(desde) or kpi_service._rango_default()[0]
    h = _parse_iso(hasta) or kpi_service._rango_default()[1]

    tok = current_tenant.set(0)
    try:
        return kpi_service.ranking_talleres(db, d, h, limite=limite)
    finally:
        current_tenant.reset(tok)


@router.get(
    "/tenants/me/kpis/ranking-mis-talleres",
    response_model=List[TallerRanking],
    summary="Ranking de talleres dentro de mi tenant (para multi-sucursal)",
)
def ranking_mi_tenant(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    d = _parse_iso(desde) or kpi_service._rango_default()[0]
    h = _parse_iso(hasta) or kpi_service._rango_default()[1]
    return kpi_service.ranking_talleres(db, d, h, limite=20)
