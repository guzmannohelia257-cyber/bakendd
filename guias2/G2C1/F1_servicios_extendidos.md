# F1 — Servicios extendidos por taller

> **Pre-requisito:** ninguno (es el primero).
> **Bloquea:** F2 (cotización), F3 (cancelación).
> **Esfuerzo:** 2 días.

## Objetivo
Que cada taller declare en cuáles de las **7 categorías oficiales del enunciado** trabaja, con **tarifa base** opcional. Al crear un incidente, el backend filtra y sugiere solo talleres compatibles.

Las 7 categorías oficiales (del [ENUNCIADO_MEJORAS_A2.md](../ENUNCIADO_MEJORAS_A2.md#tipos-de-talleres-y-servicios)):

| Código | Nombre | requiere_cotizacion |
|---|---|---|
| `llantas` | Servicio de llantas | false |
| `mecanica_general` | Mecánica general | **true** |
| `electrico` | Servicio eléctrico | **true** |
| `electronico` | Servicio electrónico | **true** |
| `chaperia_pintura` | Chapería y pintura | **true** |
| `grua_auxilio` | Grúa / Auxilio vial | false |
| `rutinario` | Servicio rutinario | false |

> `requiere_cotizacion=true` significa que aplica el flujo de F2 (cotización previa). Los demás son servicios directos (precio en el momento, sin negociación).

---

## Cambios en BD

### Migración `0004_categorias_y_tarifas`

Crear con:
```bash
.\venv\Scripts\alembic.exe revision -m "0004_categorias_y_tarifas"
```

Contenido del archivo generado:

```python
"""0004_categorias_y_tarifas

- Anade columnas a categoria_problema: codigo (unique), requiere_cotizacion.
- Anade columna tarifa_base a taller_servicio.
- Upsertea las 7 categorias oficiales del enunciado.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "REEMPLAZAR_POR_HASH_GENERADO"
down_revision: Union[str, None] = "3aa3e94bded9"  # 0003
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIAS = [
    ("llantas",          "Servicio de llantas",        "Vulcanizado, parches, inflado",          False),
    ("mecanica_general", "Mecanica general",           "Motor, transmision, frenos",             True),
    ("electrico",        "Servicio electrico",         "Sistema electrico del vehiculo",         True),
    ("electronico",      "Servicio electronico",       "Diagnostico escaner, ECU, sensores",     True),
    ("chaperia_pintura", "Chaperia y pintura",         "Carroceria, pintura, danos por colision", True),
    ("grua_auxilio",     "Grua / Auxilio vial",        "Remolque de vehiculos que no arrancan",  False),
    ("rutinario",        "Servicio rutinario",         "Mantenimientos preventivos basicos",     False),
]


def upgrade() -> None:
    # 1) Columnas nuevas en categoria_problema
    op.add_column("categoria_problema", sa.Column("codigo", sa.String(length=50), nullable=True))
    op.add_column(
        "categoria_problema",
        sa.Column("requiere_cotizacion", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # 2) Upsert de categorias (idempotente)
    for codigo, nombre, desc, requiere in CATEGORIAS:
        op.execute(sa.text("""
            INSERT INTO categoria_problema (nombre, descripcion, codigo, requiere_cotizacion)
            VALUES (:nombre, :desc, :codigo, :req)
            ON CONFLICT DO NOTHING
        """).bindparams(nombre=nombre, desc=desc, codigo=codigo, req=requiere))

    # 3) Si ya existian filas con nombre coincidente, setear su codigo
    for codigo, nombre, _desc, requiere in CATEGORIAS:
        op.execute(sa.text("""
            UPDATE categoria_problema
            SET codigo = :codigo, requiere_cotizacion = :req
            WHERE LOWER(nombre) = LOWER(:nombre) AND (codigo IS NULL OR codigo <> :codigo)
        """).bindparams(codigo=codigo, nombre=nombre, req=requiere))

    # 4) Unicidad de codigo (despues del seed para no fallar si habia nulls)
    op.create_unique_constraint("uq_categoria_codigo", "categoria_problema", ["codigo"])

    # 5) Tarifa base en taller_servicio (nullable - taller decide si la usa)
    op.add_column("taller_servicio", sa.Column("tarifa_base", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("taller_servicio", "tarifa_base")
    op.drop_constraint("uq_categoria_codigo", "categoria_problema", type_="unique")
    op.drop_column("categoria_problema", "requiere_cotizacion")
    op.drop_column("categoria_problema", "codigo")
```

Aplicar:
```bash
.\venv\Scripts\alembic.exe upgrade head
```

---

## Cambios en modelos

### `app/models/catalogos.py` — extender `CategoriaProblema`

```python
class CategoriaProblema(Base):
    __tablename__ = "categoria_problema"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String(200), nullable=True)
    icono_url = Column(String(255), nullable=True)
    codigo = Column(String(50), nullable=True, unique=True)
    requiere_cotizacion = Column(Boolean, default=False, nullable=False)
```

### `app/models/taller.py` — extender `TallerServicio`

```python
class TallerServicio(Base):
    __tablename__ = "taller_servicio"
    __table_args__ = (
        UniqueConstraint("id_taller", "id_categoria", name="uq_taller_categoria"),
    )

    id_taller_servicio = Column(Integer, primary_key=True, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False)
    id_categoria = Column(Integer, ForeignKey("categoria_problema.id_categoria"), nullable=False)
    servicio_movil = Column(Boolean, default=False, nullable=False)
    tarifa_base = Column(Numeric(10, 2), nullable=True)  # NUEVO

    taller = relationship("Taller", back_populates="servicios")
    categoria = relationship("CategoriaProblema")
```

(Recordar `from sqlalchemy import Numeric` arriba.)

---

## Schemas Pydantic

### `app/schemas/catalogo_schema.py` (nuevo)

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: int
    codigo: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    requiere_cotizacion: bool
    icono_url: Optional[str] = None
```

### `app/schemas/taller_schema.py` — añadir al final

```python
class TallerServicioCreate(BaseModel):
    id_categoria: int = Field(..., gt=0)
    servicio_movil: bool = False
    tarifa_base: Optional[float] = Field(None, ge=0)


class TallerServicioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_taller_servicio: int
    id_taller: int
    id_categoria: int
    servicio_movil: bool
    tarifa_base: Optional[float] = None


class TallerConServicios(TallerResponse):
    """Taller incluyendo lista de servicios que ofrece."""
    servicios: list[TallerServicioResponse] = []


class ActualizarServiciosTallerRequest(BaseModel):
    """
    Reemplaza la lista completa de servicios del taller (idempotente).
    """
    servicios: list[TallerServicioCreate]


class TallerCompatibleResponse(TallerResponse):
    """Taller candidato para un incidente, incluye distancia."""
    distancia_km: Optional[float] = None
    tarifa_base: Optional[float] = None
    rating_promedio: Optional[float] = None
```

Y agregar a `app/schemas/__init__.py` los exports.

---

## Endpoints

### Endpoint 1 — Listar categorías (público, lo consumen Flutter y Angular)

`app/api/catalogos.py` (nuevo):

```python
"""Endpoints de catalogos publicos: categorias, prioridades, estados."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalogos import CategoriaProblema
from app.schemas.catalogo_schema import CategoriaResponse


router = APIRouter(tags=["Catalogos"])


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(CategoriaProblema).order_by(CategoriaProblema.nombre).all()
```

Registrar en `app/api/__init__.py`:
```python
from app.api.catalogos import router as catalogos_router
__all__ = [..., "catalogos_router"]
```

Y en `app/main.py`:
```python
from app.api import (..., catalogos_router)
app.include_router(catalogos_router)
```

### Endpoint 2 — Declarar/actualizar servicios del taller

En `app/api/talleres.py`, añadir:

```python
from sqlalchemy import select
from app.models.taller import TallerServicio
from app.schemas.taller_schema import (
    ActualizarServiciosTallerRequest,
    TallerServicioResponse,
)


@router.get(
    "/mi-taller/servicios",
    response_model=List[TallerServicioResponse],
    summary="Listar mis servicios declarados",
)
def listar_mis_servicios(
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    return (
        db.query(TallerServicio)
        .filter(TallerServicio.id_taller == current_taller.id_taller)
        .all()
    )


@router.put(
    "/mi-taller/servicios",
    response_model=List[TallerServicioResponse],
    summary="Reemplaza la lista completa de servicios de mi taller",
)
def actualizar_servicios(
    body: ActualizarServiciosTallerRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    # Validacion: categorias existen
    categorias_pedidas = {s.id_categoria for s in body.servicios}
    if categorias_pedidas:
        existentes = {
            c.id_categoria
            for c in db.query(CategoriaProblema)
            .filter(CategoriaProblema.id_categoria.in_(categorias_pedidas))
            .all()
        }
        faltantes = categorias_pedidas - existentes
        if faltantes:
            raise HTTPException(400, f"Categorias inexistentes: {sorted(faltantes)}")

    # Borrar lo viejo y crear lo nuevo (estrategia replace-all simple)
    db.query(TallerServicio).filter(
        TallerServicio.id_taller == current_taller.id_taller
    ).delete()

    nuevos = [
        TallerServicio(
            id_taller=current_taller.id_taller,
            id_categoria=s.id_categoria,
            servicio_movil=s.servicio_movil,
            tarifa_base=s.tarifa_base,
        )
        for s in body.servicios
    ]
    db.add_all(nuevos)
    db.commit()
    for n in nuevos:
        db.refresh(n)
    return nuevos
```

### Endpoint 3 — Talleres compatibles para una categoría/ubicación

En `app/api/talleres.py` (público, lo usa el cliente al reportar):

```python
from math import radians, sin, cos, asin, sqrt
from typing import Optional


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return 2 * R * asin(sqrt(a))


@router.get(
    "/compatibles",
    response_model=List[TallerCompatibleResponse],
    summary="Talleres que atienden una categoria, ordenados por cercania",
)
def talleres_compatibles(
    id_categoria: int,
    latitud: float,
    longitud: float,
    radio_km: float = 20.0,
    db: Session = Depends(get_db),
):
    """
    Publico (cliente reportando). NO requiere tenant. Devuelve top-10
    talleres que tienen el servicio, ordenados por distancia.
    """
    candidatos = (
        db.query(Taller, TallerServicio)
        .join(TallerServicio, TallerServicio.id_taller == Taller.id_taller)
        .filter(
            TallerServicio.id_categoria == id_categoria,
            Taller.activo == True,        # noqa: E712
            Taller.disponible == True,    # noqa: E712
            Taller.latitud.isnot(None),
            Taller.longitud.isnot(None),
        )
        .all()
    )

    resultado = []
    for taller, servicio in candidatos:
        d = _haversine_km(latitud, longitud, taller.latitud, taller.longitud)
        if d > radio_km:
            continue
        item = TallerCompatibleResponse.model_validate(taller)
        item.distancia_km = round(d, 2)
        item.tarifa_base = float(servicio.tarifa_base) if servicio.tarifa_base else None
        # rating_promedio si quieres: calcular avg de Evaluacion.estrellas
        resultado.append(item)

    resultado.sort(key=lambda x: x.distancia_km or 9999)
    return resultado[:10]
```

> Este endpoint **no requiere tenant** porque lo usa el cliente final (público). El filtro global no aplica porque `current_tenant.get()` es None en ese contexto.

---

## Frontend
- **Web Angular**: ver [G2WEB/W1_servicios.md](../G2WEB/W1_servicios.md)
- **Mobile Flutter**: ver [G2MOBILE/M1_seleccionar_taller.md](../G2MOBILE/M1_seleccionar_taller.md)

---

## Tests (parciales — el resto en F4)

`tests/test_servicios.py`:

```python
"""Tests de servicios extendidos (F1)."""
import uuid


def test_listar_categorias_devuelve_las_7_oficiales(client):
    r = client.get("/categorias")
    assert r.status_code == 200
    codigos = {c["codigo"] for c in r.json() if c["codigo"]}
    esperadas = {
        "llantas", "mecanica_general", "electrico", "electronico",
        "chaperia_pintura", "grua_auxilio", "rutinario",
    }
    assert esperadas.issubset(codigos)


def test_chaperia_requiere_cotizacion(client):
    r = client.get("/categorias")
    chap = next(c for c in r.json() if c["codigo"] == "chaperia_pintura")
    assert chap["requiere_cotizacion"] is True


def test_llantas_NO_requiere_cotizacion(client):
    r = client.get("/categorias")
    llantas = next(c for c in r.json() if c["codigo"] == "llantas")
    assert llantas["requiere_cotizacion"] is False


def test_taller_declara_servicios(client, tenant_factory, taller_factory, taller_auth_headers, db_session):
    from app.models.catalogos import CategoriaProblema

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    headers = taller_auth_headers(taller)

    cat_llantas = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    cat_grua = db_session.query(CategoriaProblema).filter_by(codigo="grua_auxilio").one()

    body = {
        "servicios": [
            {"id_categoria": cat_llantas.id_categoria, "servicio_movil": True, "tarifa_base": 30.0},
            {"id_categoria": cat_grua.id_categoria, "servicio_movil": True, "tarifa_base": 80.0},
        ]
    }
    r = client.put("/talleres/mi-taller/servicios", json=body, headers=headers)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 2


def test_filtro_compatibles_excluye_talleres_sin_servicio(client, tenant_factory, taller_factory, db_session):
    """
    Crea 2 talleres con servicios distintos y verifica que solo aparece
    el que tiene la categoria pedida.
    """
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_llantas = taller_factory(tenant_a)
    taller_chaperia = taller_factory(tenant_b)

    # Coordenadas (La Paz centro)
    taller_llantas.latitud, taller_llantas.longitud = -16.5, -68.15
    taller_chaperia.latitud, taller_chaperia.longitud = -16.5, -68.15
    db_session.commit()

    cat_llantas = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    cat_chap = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    db_session.add_all([
        TallerServicio(id_taller=taller_llantas.id_taller, id_categoria=cat_llantas.id_categoria),
        TallerServicio(id_taller=taller_chaperia.id_taller, id_categoria=cat_chap.id_categoria),
    ])
    db_session.commit()

    r = client.get(
        "/talleres/compatibles",
        params={"id_categoria": cat_llantas.id_categoria, "latitud": -16.5, "longitud": -68.15}
    )
    assert r.status_code == 200
    ids = {t["id_taller"] for t in r.json()}
    assert taller_llantas.id_taller in ids
    assert taller_chaperia.id_taller not in ids


def test_compatibles_respeta_radio_km(client, tenant_factory, taller_factory, db_session):
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    tenant = tenant_factory()
    taller_lejos = taller_factory(tenant)
    taller_lejos.latitud, taller_lejos.longitud = -17.7833, -63.1821  # Santa Cruz
    db_session.commit()

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    db_session.add(TallerServicio(
        id_taller=taller_lejos.id_taller, id_categoria=cat.id_categoria
    ))
    db_session.commit()

    # Buscar desde La Paz con radio chico
    r = client.get(
        "/talleres/compatibles",
        params={"id_categoria": cat.id_categoria, "latitud": -16.5, "longitud": -68.15, "radio_km": 50}
    )
    assert r.status_code == 200
    ids = {t["id_taller"] for t in r.json()}
    assert taller_lejos.id_taller not in ids  # esta a >800km
```

---

## Checklist de cierre F1
- [ ] Migración `0004` aplicada (`alembic current` muestra el hash de 0004).
- [ ] `GET /categorias` devuelve las 7 con `codigo` y `requiere_cotizacion`.
- [ ] Taller autenticado puede declarar servicios (`PUT /talleres/mi-taller/servicios`).
- [ ] `GET /talleres/compatibles?...` filtra por categoría y radio.
- [ ] Tests del archivo `tests/test_servicios.py` verdes (≥6 tests).
- [ ] Pantalla Angular "Mis servicios" lista los 7 tipos y guarda.
- [ ] Pantalla Flutter "Seleccionar taller" usa el endpoint compatible.

## Si algo sale mal
- Si la migración falla por "constraint already exists" → ejecutar `alembic downgrade -1` y editar la migración con `IF NOT EXISTS`.
- Si `GET /categorias` devuelve menos de 7 → revisar que el `INSERT … ON CONFLICT DO NOTHING` no esté chocando con un constraint distinto. Borrar manualmente filas viejas duplicadas si es desarrollo.
- Si el filtro tenant rompe `GET /compatibles` → confirmar que el endpoint **NO** usa `require_tenant` (es público).
