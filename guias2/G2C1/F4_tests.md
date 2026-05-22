# F4 — Tests del Ciclo 1

> **Pre-requisito:** F1, F2 y F3 completados.
> **Esfuerzo:** continuo (mientras se implementa cada feature) + 0.5 día de tests E2E al cierre.

## Objetivo
Llegar al cierre del Ciclo 1 con **≥50 tests verdes** (los 25 actuales + ~25 nuevos), cubriendo los 3 nuevos dominios.

---

## 1. Extender `tests/conftest.py` con fixtures de cliente

Los tests de F1/F2/F3 necesitan crear clientes (usuarios rol=1), vehículos e incidentes. Agregar al final de `tests/conftest.py`:

```python
# ============================================================
# FIXTURES ADICIONALES PARA CICLO 1
# ============================================================

@pytest.fixture()
def cliente_factory(db_session):
    """Crea usuarios con rol=1 (cliente) listos para autenticarse."""
    def _make(email: str | None = None, password: str = "cliente123") -> Usuario:
        email = email or f"cliente-{uuid.uuid4().hex[:6]}@cli.example.com"
        u = Usuario(
            id_rol=1,
            nombre=f"Cliente {email}",
            email=email,
            password_hash=hash_password(password),
        )
        db_session.add(u); db_session.commit(); db_session.refresh(u)
        return u
    return _make


@pytest.fixture()
def cliente_auth_headers():
    """Headers Bearer para un cliente (sin id_tenant en el JWT)."""
    def _make(cliente: Usuario) -> dict:
        token = create_access_token(subject_id=cliente.id_usuario, tipo="usuario")
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture()
def vehiculo_factory(db_session):
    """Crea vehiculos asociados a un cliente."""
    from app.models.usuario import Vehiculo

    def _make(cliente: Usuario, placa: str | None = None) -> Vehiculo:
        v = Vehiculo(
            id_usuario=cliente.id_usuario,
            placa=placa or f"TEST-{uuid.uuid4().hex[:4].upper()}",
            marca="Toyota",
            modelo="Hilux",
            anio=2020,
            color="blanco",
        )
        db_session.add(v); db_session.commit(); db_session.refresh(v)
        return v
    return _make


@pytest.fixture()
def incidente_factory(db_session):
    """
    Crea un incidente con categoria opcional. Si no se especifica categoria,
    usa la primera del catalogo.
    """
    from app.models.catalogos import CategoriaProblema, EstadoIncidente
    from app.models.incidente import Incidente

    def _make(cliente, vehiculo, categoria_codigo: str | None = None, lat=-16.5, lng=-68.15):
        estado = db_session.query(EstadoIncidente).first()
        if categoria_codigo:
            cat = db_session.query(CategoriaProblema).filter_by(codigo=categoria_codigo).one()
        else:
            cat = db_session.query(CategoriaProblema).first()
        inc = Incidente(
            id_usuario=cliente.id_usuario,
            id_vehiculo=vehiculo.id_vehiculo,
            id_estado=estado.id_estado,
            id_categoria=cat.id_categoria if cat else None,
            latitud=lat,
            longitud=lng,
        )
        db_session.add(inc); db_session.commit(); db_session.refresh(inc)
        return inc
    return _make
```

---

## 2. Tests E2E del flujo completo

Crear `tests/test_e2e_ciclo1.py` — atraviesa todas las features del ciclo:

```python
"""
E2E del ciclo 1:
  Cliente reporta incidente (chaperia)
   → solicita cotizaciones a 3 talleres
   → cada taller responde con precio
   → cliente acepta la mas barata
   → se crea Asignacion
   → cliente cancela despues de aceptar
   → se calcula compensacion 50%
"""


def test_flujo_completo_cotizacion_y_cancelacion(
    client, db_session,
    tenant_factory, taller_factory,
    cliente_factory, vehiculo_factory, incidente_factory,
    cliente_auth_headers, taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion
    from app.models.incidente import Asignacion
    from app.models.taller import TallerServicio

    # ---- Setup ----
    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    talleres = []
    for i in range(3):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        taller.tarifa_traslado = 20
        db_session.add(TallerServicio(
            id_taller=taller.id_taller,
            id_categoria=cat.id_categoria,
            tarifa_base=300 + i * 50,  # 300, 350, 400
        ))
        talleres.append(taller)
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = incidente_factory(cliente, vehiculo, categoria_codigo="chaperia_pintura")
    cli_h = cliente_auth_headers(cliente)

    # ---- 1. Cliente solicita cotizaciones ----
    r = client.post(
        f"/incidentes/{incidente.id_incidente}/cotizaciones/solicitar",
        json={"radio_km": 50, "max_talleres": 3, "validez_horas": 2},
        headers=cli_h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["invitadas"] == 3

    # ---- 2. Cada taller responde ----
    cotizaciones = (
        db_session.query(Cotizacion)
        .filter_by(id_incidente=incidente.id_incidente)
        .all()
    )
    assert len(cotizaciones) == 3

    precios_por_taller = {}
    for i, cot in enumerate(cotizaciones):
        taller = next(t for t in talleres if t.id_taller == cot.id_taller)
        precio_servicio = 200 + i * 100  # 200, 300, 400
        precios_por_taller[taller.id_taller] = precio_servicio
        r = client.post(
            f"/cotizaciones/{cot.id_cotizacion}/responder",
            json={
                "monto_servicio": precio_servicio,
                "monto_repuestos": 100,
                "garantia_dias": 30,
                "nota": f"Taller {i}",
            },
            headers=taller_auth_headers(taller),
        )
        assert r.status_code == 200, r.text

    # ---- 3. Cliente compara ----
    r = client.get(f"/incidentes/{incidente.id_incidente}/cotizaciones", headers=cli_h)
    assert r.status_code == 200
    recibidas = r.json()
    assert len(recibidas) == 3
    assert all(c["monto_servicio"] is not None for c in recibidas)

    # ---- 4. Acepta la mas barata ----
    mas_barata = min(recibidas, key=lambda c: c["monto_servicio"])
    r = client.post(f"/cotizaciones/{mas_barata['id_cotizacion']}/aceptar", headers=cli_h)
    assert r.status_code == 200
    id_asig = r.json()["id_asignacion"]
    taller_ganador_id = r.json()["id_taller"]
    assert precios_por_taller[taller_ganador_id] == 200  # el mas barato

    # Las otras 2 deben estar rechazadas
    db_session.commit()  # asegurar refresh
    rechazadas = [
        c for c in db_session.query(Cotizacion).filter_by(id_incidente=incidente.id_incidente).all()
        if c.estado.nombre == "rechazada"
    ]
    assert len(rechazadas) == 2

    # ---- 5. Cliente cancela despues de aceptar (estado aceptada -> compensacion 50%) ----
    r = client.post(
        f"/asignaciones/{id_asig}/cancelar",
        json={"motivo": "Llego el seguro, pago la mitad del traslado"},
        headers=cli_h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nuevo_estado"] == "cancelada"
    # tarifa_traslado=20, factor 50% -> compensacion 10
    assert data["compensacion_monto"] == 10.0
    assert data["compensacion_pagada"] is False  # hay que pagar 10
```

---

## 3. Cobertura mínima

Al cierre del Ciclo 1 debe haber, como mínimo:

| Archivo | Tests | Cubre |
|---|---|---|
| `tests/test_plans.py` | 3 | ✅ ya existe |
| `tests/test_signup.py` | 7 | ✅ ya existe |
| `tests/test_tenants_crud.py` | 11 | ✅ ya existe |
| `tests/test_tenant_isolation.py` | 4 | ✅ ya existe |
| `tests/test_servicios.py` | ≥6 | F1 |
| `tests/test_cotizaciones.py` | ≥6 | F2 |
| `tests/test_cancelacion.py` | ≥6 | F3 |
| `tests/test_e2e_ciclo1.py` | 1 | E2E |
| **TOTAL** | **≥44** | |

Si bajamos de ~44 al final, hay un hueco — agregar tests de validación (422, 401, 403) hasta llegar.

---

## 4. Comando único para correr todo

Documentar en `README.md` del backend:

```bash
# Tests rápidos (sin logs sql)
DEBUG=False .\venv\Scripts\python.exe -m pytest tests/

# Con cobertura (instalar primero: pip install pytest-cov)
DEBUG=False .\venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-report=term-missing

# Solo un archivo
DEBUG=False .\venv\Scripts\python.exe -m pytest tests/test_cotizaciones.py -v

# Detener en el primer fallo
DEBUG=False .\venv\Scripts\python.exe -m pytest tests/ -x
```

PowerShell equivalent:
```powershell
$env:DEBUG="False"; .\venv\Scripts\python.exe -m pytest tests/
```

---

## 5. Aceptación final del Ciclo 1

Al cierre (29 mayo) debe ser cierto que:

- [ ] `alembic upgrade head` aplica limpio (en BD vacía y en BD con datos).
- [ ] `pytest tests/` → **0 fallos, 0 errores**.
- [ ] Cobertura ≥ 50% (instalar `pytest-cov` para medirlo).
- [ ] Swagger en `/docs` muestra los nuevos endpoints.
- [ ] Demo manual reproducible:
  1. `POST /signup` crea tenant + taller.
  2. Taller declara servicios con `PUT /talleres/mi-taller/servicios`.
  3. Cliente reporta incidente de chapería.
  4. Cliente solicita cotizaciones → recibe 3.
  5. 3 talleres responden → cliente compara → acepta la mejor.
  6. Cliente cancela → ve compensación calculada.

## Anti-patrones a evitar
- ❌ **Marcar test "passed" con `pytest.skip`** porque falta implementación. Si la feature no está, el test ni siquiera debe existir todavía.
- ❌ **Tests que dependen de orden de ejecución**. Cada test es independiente (rollback automático del SAVEPOINT).
- ❌ **Hardcodear `id_categoria=1`** en lugar de buscar por `codigo="llantas"`. Los IDs cambian entre BDs.
- ❌ **Commitear `print()` de debug**. Si necesitas debuggear: `pytest -s` muestra los prints sin contaminar el código.
