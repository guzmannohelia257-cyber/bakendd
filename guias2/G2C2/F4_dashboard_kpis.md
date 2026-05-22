# F4 — Dashboard de KPIs

> **Pre-requisito:** ninguno técnico (puede correr en paralelo a F1-F3).
> **Esfuerzo:** 2 días.

## Objetivo (del enunciado)
Dashboard con 4 indicadores:

| KPI | Cálculo |
|---|---|
| Tiempo promedio de asignación | avg(`asignacion.created_at` − `incidente.created_at`) — solo asignaciones aceptadas |
| Tiempo promedio de llegada | avg(estado `llegado` − estado `aceptada`) por asignación, vía `historial_estado_asignacion` |
| Incidentes por tipo | count agrupado por `categoria_problema.codigo` |
| Talleres más eficientes | ranking por composite score (tiempo + rating + tasa de aceptación) |

Filtros: `desde`, `hasta`, `id_tenant` (auto desde el filtro tenant).

---

## Estrategia
Cálculo **on-the-fly** con SQL agregado. No necesitamos cron + tabla materializada para el parcial — el volumen es bajo. Si después crece, hacer vista materializada refrescada cada 5 min.

Cache opcional en Redis con TTL 60s (ya hay cliente).

---

## Servicio `app/services/kpi_service.py`

```python
"""
Calculo de KPIs por tenant.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalogos import CategoriaProblema, EstadoAsignacion
from app.models.incidente import (
    Asignacion,
    Evaluacion,
    HistorialEstadoAsignacion,
    Incidente,
    CandidatoAsignacion,
)
from app.models.taller import Taller


def _rango_default():
    """Default: ultimos 30 dias hasta hoy."""
    hasta = datetime.now(timezone.utc)
    desde = hasta - timedelta(days=30)
    return desde, hasta


def tiempo_promedio_asignacion_min(
    db: Session, desde: datetime, hasta: datetime, id_tenant: Optional[int] = None,
) -> float:
    """
    Promedio en minutos desde que el cliente crea el incidente
    hasta que se crea la primera asignacion aceptada.
    """
    estado_aceptada = (
        db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    )
    if not estado_aceptada:
        return 0.0

    q = (
        select(
            func.avg(
                func.extract("epoch", Asignacion.created_at - Incidente.created_at) / 60
            )
        )
        .select_from(Asignacion)
        .join(Incidente, Incidente.id_incidente == Asignacion.id_incidente)
        .where(
            Asignacion.created_at.between(desde, hasta),
        )
    )
    if id_tenant is not None:
        q = q.where(Asignacion.id_tenant == id_tenant)

    val = db.execute(q).scalar()
    return float(val or 0)


def tiempo_promedio_llegada_min(
    db: Session, desde: datetime, hasta: datetime, id_tenant: Optional[int] = None,
) -> float:
    """
    Promedio en minutos entre transicion 'aceptada' -> 'llegado' (o 'en_camino'),
    leido de historial_estado_asignacion.
    """
    estado_llegado = db.query(EstadoAsignacion).filter_by(nombre="llegado").first()
    estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    if not (estado_llegado and estado_aceptada):
        return 0.0

    # Subquery: timestamp del estado aceptada por asignacion
    sub_acept = (
        select(
            HistorialEstadoAsignacion.id_asignacion.label("aid"),
            func.min(HistorialEstadoAsignacion.created_at).label("ts_aceptada"),
        )
        .where(HistorialEstadoAsignacion.id_estado_nuevo == estado_aceptada.id_estado_asignacion)
        .group_by(HistorialEstadoAsignacion.id_asignacion)
        .subquery()
    )

    sub_llego = (
        select(
            HistorialEstadoAsignacion.id_asignacion.label("aid"),
            func.min(HistorialEstadoAsignacion.created_at).label("ts_llego"),
        )
        .where(HistorialEstadoAsignacion.id_estado_nuevo == estado_llegado.id_estado_asignacion)
        .group_by(HistorialEstadoAsignacion.id_asignacion)
        .subquery()
    )

    q = (
        select(
            func.avg(func.extract("epoch", sub_llego.c.ts_llego - sub_acept.c.ts_aceptada) / 60)
        )
        .select_from(sub_acept)
        .join(sub_llego, sub_llego.c.aid == sub_acept.c.aid)
        .join(Asignacion, Asignacion.id_asignacion == sub_acept.c.aid)
        .where(sub_llego.c.ts_llego.between(desde, hasta))
    )
    if id_tenant is not None:
        q = q.where(Asignacion.id_tenant == id_tenant)

    val = db.execute(q).scalar()
    return float(val or 0)


def incidentes_por_categoria(
    db: Session, desde: datetime, hasta: datetime, id_tenant: Optional[int] = None,
) -> list[dict]:
    q = (
        select(
            CategoriaProblema.codigo,
            CategoriaProblema.nombre,
            func.count(Incidente.id_incidente).label("total"),
        )
        .select_from(Incidente)
        .join(CategoriaProblema, CategoriaProblema.id_categoria == Incidente.id_categoria)
        .where(Incidente.created_at.between(desde, hasta))
        .group_by(CategoriaProblema.codigo, CategoriaProblema.nombre)
        .order_by(func.count(Incidente.id_incidente).desc())
    )
    if id_tenant is not None:
        q = q.where(Incidente.id_tenant == id_tenant)

    return [
        {"codigo": r.codigo, "nombre": r.nombre, "total": int(r.total)}
        for r in db.execute(q).all()
    ]


def ranking_talleres(
    db: Session, desde: datetime, hasta: datetime, limite: int = 10,
) -> list[dict]:
    """
    Ranking GLOBAL por tenant (super-admin). Para listar talleres dentro de
    un tenant especifico, agregar where Taller.id_tenant=...
    """
    estado_completada = db.query(EstadoAsignacion).filter_by(nombre="completada").first()

    # rating promedio por taller
    sub_rating = (
        select(
            Evaluacion.id_taller,
            func.avg(Evaluacion.estrellas).label("rating"),
            func.count(Evaluacion.id_evaluacion).label("n_eval"),
        )
        .where(Evaluacion.created_at.between(desde, hasta))
        .group_by(Evaluacion.id_taller)
        .subquery()
    )

    # completadas y tiempo promedio de llegada
    sub_completadas = (
        select(
            Asignacion.id_taller,
            func.count(Asignacion.id_asignacion).label("n_completadas"),
        )
        .where(
            Asignacion.id_estado_asignacion == (estado_completada.id_estado_asignacion if estado_completada else -1),
            Asignacion.updated_at.between(desde, hasta),
        )
        .group_by(Asignacion.id_taller)
        .subquery()
    )

    # candidatos vs aceptaciones (tasa de aceptacion)
    sub_candidatos = (
        select(
            CandidatoAsignacion.id_taller,
            func.count(CandidatoAsignacion.id_candidato).label("n_cand"),
            func.sum(func.cast(CandidatoAsignacion.seleccionado, func.Integer)).label("n_acept"),
        )
        .group_by(CandidatoAsignacion.id_taller)
        .subquery()
    )

    q = (
        select(
            Taller.id_taller,
            Taller.nombre,
            sub_rating.c.rating,
            sub_completadas.c.n_completadas,
            sub_candidatos.c.n_cand,
            sub_candidatos.c.n_acept,
        )
        .select_from(Taller)
        .outerjoin(sub_rating, sub_rating.c.id_taller == Taller.id_taller)
        .outerjoin(sub_completadas, sub_completadas.c.id_taller == Taller.id_taller)
        .outerjoin(sub_candidatos, sub_candidatos.c.id_taller == Taller.id_taller)
        .where(Taller.activo.is_(True))
    )

    filas = db.execute(q).all()

    # Score compuesto: rating*0.5 + tasa_aceptacion*0.3 + log(n_completadas+1)*0.2
    import math
    resultado = []
    for r in filas:
        rating = float(r.rating or 0)
        n_cand = int(r.n_cand or 0)
        n_acept = int(r.n_acept or 0)
        tasa = (n_acept / n_cand) if n_cand else 0
        n_comp = int(r.n_completadas or 0)
        score = (rating / 5.0) * 0.5 + tasa * 0.3 + min(math.log(n_comp + 1) / 5, 1) * 0.2

        resultado.append({
            "id_taller": r.id_taller,
            "nombre": r.nombre,
            "rating_promedio": round(rating, 2),
            "completadas": n_comp,
            "tasa_aceptacion": round(tasa, 2),
            "score": round(score, 3),
        })

    resultado.sort(key=lambda x: x["score"], reverse=True)
    return resultado[:limite]


def resumen_completo(
    db: Session, desde: Optional[datetime] = None, hasta: Optional[datetime] = None,
    id_tenant: Optional[int] = None,
) -> dict:
    if desde is None or hasta is None:
        desde, hasta = _rango_default()
    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "tiempo_promedio_asignacion_min": round(
            tiempo_promedio_asignacion_min(db, desde, hasta, id_tenant), 2
        ),
        "tiempo_promedio_llegada_min": round(
            tiempo_promedio_llegada_min(db, desde, hasta, id_tenant), 2
        ),
        "incidentes_por_categoria": incidentes_por_categoria(db, desde, hasta, id_tenant),
    }
```

---

## Schemas `app/schemas/kpi_schema.py`

```python
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
```

---

## Endpoints `app/api/kpis.py`

```python
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

    # El filtro global ya scopea al tenant del JWT, pero pasamos explicito
    # para no depender solo del filtro.
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

    # Super-admin ve todo: bypass del filtro
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
    # Con tenant en contexto, el filtro global scopea a su tenant
    # (ranking_talleres tiene Taller.activo, y el listener inyecta id_tenant)
    return kpi_service.ranking_talleres(db, d, h, limite=20)
```

Registrar en `app/api/__init__.py` y `app/main.py`.

---

## Frontend
- **Web Angular (dashboard con Chart.js)**: ver [G2WEB/W6_kpis_dashboard.md](../G2WEB/W6_kpis_dashboard.md)

---

## Tests `tests/test_kpis.py`

```python
"""Tests del calculo de KPIs."""
from datetime import datetime, timedelta, timezone


def _now():
    return datetime.now(timezone.utc)


def test_kpi_resumen_endpoint(
    client, db_session, tenant_factory, taller_factory, taller_auth_headers,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "tiempo_promedio_asignacion_min" in data
    assert "incidentes_por_categoria" in data
    assert isinstance(data["incidentes_por_categoria"], list)


def test_kpi_incidentes_por_categoria_agrupa(
    client, db_session, tenant_factory, taller_factory, taller_auth_headers,
    cliente_factory, vehiculo_factory, incidente_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import Incidente

    tenant = tenant_factory()
    taller = taller_factory(tenant)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    # 3 incidentes llantas, 1 chaperia, todos asociados a este tenant
    for _ in range(3):
        inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")
        inc.id_tenant = tenant.id_tenant
    incidente_factory(cliente, vehiculo, categoria_codigo="chaperia_pintura").id_tenant = tenant.id_tenant
    db_session.commit()

    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller))
    cats = {c["codigo"]: c["total"] for c in r.json()["incidentes_por_categoria"]}
    assert cats.get("llantas") == 3
    assert cats.get("chaperia_pintura") == 1


def test_kpi_tiempo_asignacion_calcula(
    db_session, tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
):
    """Test directo del servicio."""
    from datetime import timedelta
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion
    from app.services import kpi_service

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    inc.id_tenant = tenant.id_tenant
    db_session.commit()

    estado_aceptada = db_session.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db_session.add(asig)
    db_session.commit()

    # Forzar created_at viejo del incidente (10 min atras)
    db_session.execute(
        "UPDATE incidente SET created_at = NOW() - INTERVAL '10 minutes' WHERE id_incidente = :i",
        {"i": inc.id_incidente},
    )
    db_session.commit()

    promedio = kpi_service.tiempo_promedio_asignacion_min(
        db_session, _now() - timedelta(hours=1), _now(), id_tenant=tenant.id_tenant,
    )
    assert promedio >= 9 and promedio <= 11  # ~10 min


def test_ranking_talleres_super_admin(
    client, db_session, admin_headers, tenant_factory, taller_factory,
):
    tenant = tenant_factory()
    taller_factory(tenant)
    r = client.get("/admin/kpis/ranking-talleres", headers=admin_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_kpi_aisla_por_tenant(
    client, db_session, tenant_factory, taller_factory, taller_auth_headers,
    cliente_factory, vehiculo_factory, incidente_factory,
):
    """KPI de tenant A no incluye incidentes de tenant B."""
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_factory(tenant_b)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    # 2 incidentes para tenant B
    for _ in range(2):
        inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")
        inc.id_tenant = tenant_b.id_tenant
    # 1 para tenant A
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")
    inc.id_tenant = tenant_a.id_tenant
    db_session.commit()

    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller_a))
    cats = {c["codigo"]: c["total"] for c in r.json()["incidentes_por_categoria"]}
    assert cats.get("llantas") == 1  # NO debe ver los 2 de tenant_b
```

---

## Checklist de cierre F4
- [ ] `app/services/kpi_service.py` con 4 funciones de cálculo.
- [ ] `GET /tenants/me/kpis` devuelve los 3 indicadores básicos.
- [ ] `GET /admin/kpis/ranking-talleres` accesible solo a rol=4.
- [ ] Filtros `desde` / `hasta` funcionan.
- [ ] KPIs respetan aislamiento tenant (verified por test).
- [ ] Dashboard Angular muestra los 4 KPIs con al menos 1 gráfico Chart.js.
- [ ] Tests `tests/test_kpis.py` verdes (≥5).

## Notas
- **Aislamiento cross-tenant**: confiamos en el filtro global + pasamos `id_tenant` explícito por defensa en profundidad.
- **Performance**: si los queries tardan > 200ms con datos reales, cachear en Redis con `get_redis().setex(key, 60, json.dumps(data))`.
- **Materializar**: si se necesita, crear tabla `kpi_diario_taller` con un job que corre cron. Para parcial no es necesario.
- **Postgres `extract('epoch', interval)`**: cuidado con timezone — usar columnas `TIMESTAMPTZ` (los modelos ya usan `DateTime(timezone=True)`).
