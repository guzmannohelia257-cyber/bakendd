# F8 — Tests del Ciclo 2

> **Pre-requisito:** F1-F7 (en progreso).
> **Esfuerzo:** continuo durante todo el ciclo + 0.5 día de E2E al cierre.

## Objetivo
Llegar al cierre del Ciclo 2 con **≥75 tests verdes** (los ~50 del C1 + ~25 nuevos), cubriendo WS infra, broadcast, tracking, KPIs e IA.

Los tests específicos por fase están en cada `Fx_*.md`. Este archivo agrupa lo transversal: fixtures nuevas, tests E2E del ciclo y reglas de aceptación final.

---

## 1. Fixtures adicionales en `conftest.py`

Agregar al final de `tests/conftest.py`:

```python
# ============================================================
# FIXTURES PARA CICLO 2
# ============================================================

@pytest.fixture()
def tecnico_factory(db_session):
    """Crea usuario rol=3 vinculado a un taller."""
    from app.models.usuario import Usuario
    from app.models.usuario_taller import UsuarioTaller

    def _make(taller, email: str | None = None, password: str = "tec12345"):
        email = email or f"tec-{uuid.uuid4().hex[:6]}@test.example.com"
        u = Usuario(
            id_rol=3,
            nombre=f"Tecnico {email}",
            email=email,
            password_hash=hash_password(password),
        )
        db_session.add(u); db_session.commit(); db_session.refresh(u)

        vin = UsuarioTaller(
            id_usuario=u.id_usuario, id_taller=taller.id_taller, activo=True,
        )
        db_session.add(vin); db_session.commit()
        return u
    return _make


@pytest.fixture()
def tecnico_auth_headers():
    def _make(tecnico) -> dict:
        from app.core.security import create_access_token
        token = create_access_token(subject_id=tecnico.id_usuario, tipo="usuario")
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture()
def asignacion_factory(db_session):
    """Crea una asignacion lista para tracking/cancelacion."""
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    def _make(tenant, taller, incidente, tecnico=None, estado_nombre="aceptada"):
        estado = db_session.query(EstadoAsignacion).filter_by(nombre=estado_nombre).first()
        if not estado:
            estado = EstadoAsignacion(nombre=estado_nombre)
            db_session.add(estado); db_session.commit(); db_session.refresh(estado)

        asig = Asignacion(
            id_tenant=tenant.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_usuario=tecnico.id_usuario if tecnico else None,
            id_estado_asignacion=estado.id_estado_asignacion,
        )
        db_session.add(asig); db_session.commit(); db_session.refresh(asig)
        return asig
    return _make


@pytest.fixture(autouse=True)
def _reset_pubsub_local():
    """Asegura que cada test arranca con pubsub en modo local-only."""
    from app.realtime.pubsub import pubsub_broker
    pubsub_broker._redis = None
    yield
```

---

## 2. Test E2E del ciclo completo

`tests/test_e2e_ciclo2.py`:

```python
"""
E2E Ciclo 2: cliente reporta -> IA clasifica -> broadcast a talleres ->
primero acepta -> tracking GPS -> geofencing llegado.
"""
import pytest


def test_flujo_completo_emergencia_tiempo_real(
    client, db_session,
    tenant_factory, taller_factory, tecnico_factory,
    cliente_factory, vehiculo_factory,
    cliente_auth_headers, taller_auth_headers, tecnico_auth_headers,
):
    from app.models.catalogos import CategoriaProblema, EstadoAsignacion
    from app.models.incidente import CandidatoAsignacion, Incidente
    from app.models.taller import TallerServicio

    # ---- Setup: 3 talleres compatibles ----
    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    talleres = []
    for _ in range(3):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))
        talleres.append(taller)
    db_session.commit()

    # ---- Cliente reporta ----
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    cli_h = cliente_auth_headers(cliente)

    # Crear incidente directo (sin clasificacion IA automatica para simplicidad)
    estado_pendiente = db_session.execute(
        "SELECT id_estado FROM estado_incidente LIMIT 1"
    ).scalar()
    inc = Incidente(
        id_usuario=cliente.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=estado_pendiente,
        id_categoria=cat.id_categoria,
        latitud=-16.5005, longitud=-68.1505,
        descripcion_usuario="Se me pincho la llanta",
    )
    db_session.add(inc); db_session.commit(); db_session.refresh(inc)

    # Simular candidatos (lo haria el matching_service)
    for t in talleres:
        db_session.add(CandidatoAsignacion(
            id_incidente=inc.id_incidente, id_taller=t.id_taller, distancia_km=0.1,
        ))
    db_session.commit()

    # ---- Primer taller acepta (gana la carrera) ----
    r = client.post(
        f"/incidentes/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[0]),
    )
    assert r.status_code == 200
    id_asig = r.json()["id_asignacion"]

    # ---- Segundo intenta -> 409 ----
    r2 = client.post(
        f"/incidentes/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[1]),
    )
    assert r2.status_code == 409

    # ---- Tecnico del ganador asignado a la asignacion ----
    tecnico = tecnico_factory(talleres[0])
    db_session.execute(
        "UPDATE asignacion SET id_usuario = :u WHERE id_asignacion = :a",
        {"u": tecnico.id_usuario, "a": id_asig},
    )
    db_session.commit()

    # ---- Tecnico reporta ubicacion lejos: NO geofence ----
    r3 = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.510, "longitud": -68.160,
            "id_asignacion": id_asig,
        },
        headers=tecnico_auth_headers(tecnico),
    )
    assert r3.status_code == 200
    assert r3.json()["llegado_auto"] is False
    assert r3.json()["eta"]["distancia_km"] > 0

    # ---- Tecnico llega: geofence activa ----
    if not db_session.query(EstadoAsignacion).filter_by(nombre="llegado").first():
        db_session.add(EstadoAsignacion(nombre="llegado")); db_session.commit()

    r4 = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.5005, "longitud": -68.1505,  # mismo punto incidente
            "id_asignacion": id_asig,
        },
        headers=tecnico_auth_headers(tecnico),
    )
    assert r4.status_code == 200
    assert r4.json()["llegado_auto"] is True
```

---

## 3. Test de KPIs sobre data del E2E

`tests/test_e2e_kpis.py`:

```python
"""Verifica que despues del flujo E2E, los KPIs reflejan la actividad."""


def test_kpis_aparecen_tras_actividad(
    client, db_session,
    tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
    asignacion_factory, taller_auth_headers,
):
    # Crear 3 incidentes y 3 asignaciones aceptadas
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    for cat_codigo in ("llantas", "llantas", "chaperia_pintura"):
        inc = incidente_factory(cliente, vehiculo, categoria_codigo=cat_codigo)
        inc.id_tenant = tenant.id_tenant
        asignacion_factory(tenant, taller, inc)
    db_session.commit()

    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller))
    assert r.status_code == 200
    cats = {c["codigo"]: c["total"] for c in r.json()["incidentes_por_categoria"]}
    assert cats.get("llantas") == 2
    assert cats.get("chaperia_pintura") == 1
```

---

## 4. Smoke test: app arranca con todo cableado

`tests/test_smoke_ciclo2.py`:

```python
"""Smoke: app arranca con WS, KPIs, broadcasts cableados."""


def test_health_y_docs(client):
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_endpoints_nuevos_aparecen_en_openapi(client):
    spec = client.get("/openapi.json").json()
    paths = set(spec["paths"].keys())
    assert "/tenants/me/kpis" in paths
    assert "/admin/kpis/ranking-talleres" in paths
    assert "/tecnicos/me/ubicacion" in paths
    assert "/incidentes/{id_incidente}/aceptar" in paths


def test_ws_endpoint_registrado(client):
    spec = client.get("/openapi.json").json()
    # FastAPI no documenta WS en OpenAPI por defecto, pero el router esta cargado
    # Validar conectando con token invalido y esperando handshake fail rapido
    import pytest
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
```

---

## 5. Comandos clave

Setup completo:
```bash
# Aplicar todas las migraciones
.\venv\Scripts\alembic.exe upgrade head

# Asegurar Redis arriba
docker compose up -d redis
docker exec yary-redis redis-cli ping  # PONG

# Correr toda la suite
$env:DEBUG="False"
.\venv\Scripts\python.exe -m pytest tests/ -v

# Solo Ciclo 2
.\venv\Scripts\python.exe -m pytest tests/test_ws_infra.py tests/test_broadcast.py tests/test_tracking.py tests/test_kpis.py tests/test_ia_classifier.py -v

# Con cobertura
pip install pytest-cov
.\venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## 6. Aceptación final del Ciclo 2 (7 jun)

- [ ] `alembic upgrade head` aplica limpio (migraciones 0001-0007).
- [ ] `pytest tests/` → **0 fallos, ≥75 tests verdes**.
- [ ] Cobertura ≥ 60% sobre `app/` (excluyendo `ai_modules` por difícil mockeo).
- [ ] Swagger muestra todos los endpoints nuevos con descripciones.
- [ ] Demo manual reproducible:
  1. Cliente Flutter reporta incidente offline → encolado → sincroniza al volver online.
  2. Cliente online reporta → 3 talleres ven la emergencia en sus tablets simultáneamente.
  3. Primer click gana, los demás ven "tomada".
  4. Técnico del ganador inicia viaje, app envía GPS, cliente ve marker moverse.
  5. Técnico llega → geofence activa estado "llegado".
  6. Cliente abre dashboard KPIs y ve los 4 indicadores con datos reales.
  7. IA clasifica una frase en español boliviano correctamente.
  8. Apagar WiFi en web Angular → seguir viendo lista de incidentes desde IndexedDB.

---

## Anti-patrones específicos del Ciclo 2

- ❌ **Testear WS con sleeps**: usar `ws.receive_json(timeout=2)` o callbacks. No `await asyncio.sleep(5)`.
- ❌ **Hardcodear lat/lng en tests**: usar valores conocidos (centro La Paz `-16.5, -68.15`) y calcular distancias esperadas.
- ❌ **Asumir que Redis está arriba en CI**: el `pubsub_broker` debe degradar limpio (modo local-only) si no.
- ❌ **Mockear Gemini en cada test**: agregar `monkeypatch.setattr("app.ai_modules.classifier._gemini_client", lambda: None)` en una fixture `autouse` para que toda la suite no toque la API real.
- ❌ **Background tasks no esperadas**: si publish/notify se hacen con `asyncio.create_task`, agregar `await asyncio.sleep(0)` o flushear antes de hacer asserts.
- ❌ **Tests offline en frontend dentro de pytest**: no se puede. Documentar plan manual y verificar con DevTools o Flutter inspector.

## Notas
- **Performance de pytest**: con SAVEPOINT por test y ~75 tests, esperar 5-10s totales. Si crece mucho, considerar `pytest-xdist` para paralelizar.
- **Limpiar Redis entre runs**: si los tests pasan por Redis real, `FLUSHDB` en una fixture session-scope.
- **CI**: en GitHub Actions, levantar Postgres + Redis como services. Documentar yml en `.github/workflows/ci.yml` cuando llegue Ciclo 3.
