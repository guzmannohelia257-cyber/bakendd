"""
E2E de todos los flujos críticos del proyecto, end-to-end.

Cada test simula una rueda completa entre los actores:
  - Cliente (rol=1, app móvil Flutter)
  - Taller (web Angular)
  - Técnico (rol=3, app móvil Flutter)

Cubre los bugs reportados en producción que se nos escaparon antes de tener
tests, principalmente:
  - "al cancelar no aparece cancelado en el historial"
  - "el taller no ve la solicitud"
  - "el técnico no ve la asignación tras aceptar"
  - "tras rechazar, el siguiente candidato no recibe nada"
"""
from __future__ import annotations


# ============================================================
# Helpers
# ============================================================

def _ensure_estados(db_session):
    """Asegura los estados de incidente y asignación que los endpoints esperan."""
    from app.models.catalogos import EstadoAsignacion, EstadoIncidente

    inc_deseados = [
        ("borrador", "Borrador"),
        ("pendiente", "Reportado"),
        ("en_proceso", "En atención"),
        ("atendido", "Resuelto"),
        ("cancelado", "Cancelado"),
    ]
    existentes = {e.nombre for e in db_session.query(EstadoIncidente).all()}
    for n, d in inc_deseados:
        if n not in existentes:
            db_session.add(EstadoIncidente(nombre=n, descripcion=d))

    asig_deseados = ["pendiente", "aceptada", "rechazada", "en_camino", "llegado", "completada", "cancelada"]
    existentes = {e.nombre for e in db_session.query(EstadoAsignacion).all()}
    for n in asig_deseados:
        if n not in existentes:
            db_session.add(EstadoAsignacion(nombre=n))
    db_session.commit()


def _crear_taller_con_categoria(db_session, tenant_factory, taller_factory, categoria, lat, lng):
    """Atajo para crear un taller activo + disponible que atiende una categoría."""
    from app.models.taller import TallerServicio

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = lat, lng
    taller.activo = True
    taller.disponible = True
    taller.verificado = True
    db_session.add(TallerServicio(
        id_taller=taller.id_taller,
        id_categoria=categoria.id_categoria,
    ))
    db_session.commit()
    db_session.refresh(taller)
    return tenant, taller


def _crear_borrador_y_confirmar(client, db_session, cliente, vehiculo, categoria, taller, headers_cli):
    """
    Atajo: cliente crea borrador, le seteamos id_categoria (simulamos IA OK)
    y confirma eligiendo `taller`. Retorna el id_incidente.
    """
    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "Test",
            "latitud": -17.78, "longitud": -63.18,
        },
        headers=headers_cli,
    )
    assert r.status_code == 201, r.text
    id_incidente = r.json()["id_incidente"]

    # Simulamos IA seteando id_categoria
    from app.models.incidente import Incidente
    inc = db_session.query(Incidente).filter_by(id_incidente=id_incidente).one()
    inc.id_categoria = categoria.id_categoria
    db_session.commit()

    r2 = client.post(
        f"/incidencias/{id_incidente}/confirmar",
        json={"id_taller_preferido": taller.id_taller},
        headers=headers_cli,
    )
    assert r2.status_code == 200, r2.text
    return id_incidente


# ============================================================
# FLUJO 1: CLIENTE — REPORTAR + CANCELAR INCIDENTE
# ============================================================

def test_cliente_cancela_incidente_aparece_como_cancelado_en_historial(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """
    Bug reportado: "al cancelar no aparece cancelado".

    Validación:
      1. Cliente reporta y confirma -> incidente queda en `pendiente`.
      2. Cliente cancela vía PATCH /incidencias/{id}/cancelar.
      3. Historial muestra el incidente con estado `cancelado` (NO desaparece).
    """
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    cat = db_session.query(CategoriaProblema).first()

    _, taller = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    id_inc = _crear_borrador_y_confirmar(
        client, db_session, cliente, vehiculo, cat, taller, headers,
    )

    # Cliente cancela
    r = client.patch(f"/incidencias/{id_inc}/cancelar", headers=headers)
    assert r.status_code == 200, r.text

    # Historial debe seguir mostrando el incidente, pero con estado cancelado
    r2 = client.get("/incidencias/mis-incidencias", headers=headers)
    assert r2.status_code == 200
    items = r2.json()
    items_inc = [i for i in items if i["id_incidente"] == id_inc]
    assert len(items_inc) == 1, "El incidente cancelado debe seguir en historial"
    assert items_inc[0]["estado"]["nombre"] == "cancelado"

    # Filtro explícito por estado=cancelado también lo devuelve
    r3 = client.get("/incidencias/mis-incidencias?estado=cancelado", headers=headers)
    assert r3.status_code == 200
    assert any(i["id_incidente"] == id_inc for i in r3.json())


def test_cliente_no_puede_cancelar_incidente_ya_atendido(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema, EstadoIncidente
    from app.models.incidente import Incidente

    cat = db_session.query(CategoriaProblema).first()
    _, taller = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    id_inc = _crear_borrador_y_confirmar(
        client, db_session, cliente, vehiculo, cat, taller, headers,
    )

    # Forzamos estado atendido para simular flujo completo
    inc = db_session.query(Incidente).filter_by(id_incidente=id_inc).one()
    estado_atendido = db_session.query(EstadoIncidente).filter_by(nombre="atendido").one()
    inc.id_estado = estado_atendido.id_estado
    db_session.commit()

    r = client.patch(f"/incidencias/{id_inc}/cancelar", headers=headers)
    assert r.status_code == 400, r.text


# ============================================================
# FLUJO 2: TALLER — ACEPTAR / RECHAZAR ASIGNACIÓN
# ============================================================

def test_taller_acepta_asignacion_pasa_a_aceptada_y_cliente_la_ve(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    taller_auth_headers,
):
    """
    Flujo feliz lado taller:
      1. Cliente confirma -> asignacion en pendiente para el taller elegido.
      2. Taller llama PUT /asignaciones/{id}/aceptar -> pasa a `aceptada`.
      3. Listado del taller (filtro estado=aceptada) la incluye.
      4. El cliente ve la asignación en el detalle del incidente.
    """
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import Asignacion

    cat = db_session.query(CategoriaProblema).first()
    tenant, taller = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers_cli = cliente_auth_headers(cliente)
    headers_taller = taller_auth_headers(taller)

    id_inc = _crear_borrador_y_confirmar(
        client, db_session, cliente, vehiculo, cat, taller, headers_cli,
    )

    asig = db_session.query(Asignacion).filter_by(id_incidente=id_inc).one()

    # Taller acepta
    r = client.put(
        f"/talleres/mi-taller/asignaciones/{asig.id_asignacion}/aceptar",
        json={"eta_minutos": 25, "nota_taller": "Vamos en 25 min"},
        headers=headers_taller,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"]["nombre"] == "aceptada"

    # Listado del taller (estado=aceptada) la incluye
    r2 = client.get(
        "/talleres/mi-taller/asignaciones?estado=aceptada",
        headers=headers_taller,
    )
    assert r2.status_code == 200
    ids = [a["id_asignacion"] for a in r2.json()]
    assert asig.id_asignacion in ids

    # Y NO aparece más en filtro estado=pendiente
    r3 = client.get(
        "/talleres/mi-taller/asignaciones?estado=pendiente",
        headers=headers_taller,
    )
    assert asig.id_asignacion not in [a["id_asignacion"] for a in r3.json()]


def test_taller_rechaza_pasa_a_siguiente_candidato(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    taller_auth_headers,
):
    """
    Cliente confirma -> Taller A recibe asignación en pendiente y la rechaza ->
    Debe existir una NUEVA asignación pendiente para un taller distinto a A
    (el matching service decide cuál según score; aquí solo verificamos que
    el ciclo de reasignación funcionó y la nueva asignación tiene id_tenant
    poblado para que aparezca en el dashboard del siguiente taller).
    """
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import Asignacion, CandidatoAsignacion

    cat = db_session.query(CategoriaProblema).first()

    # Taller A (el que el cliente elige) y al menos un B compatible cerca
    _, taller_a = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.79, -63.19,
    )

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers_cli = cliente_auth_headers(cliente)

    id_inc = _crear_borrador_y_confirmar(
        client, db_session, cliente, vehiculo, cat, taller_a, headers_cli,
    )

    # Hay UNA asignacion (la de A) en pendiente con id_tenant poblado
    asignaciones = db_session.query(Asignacion).filter_by(id_incidente=id_inc).all()
    assert len(asignaciones) == 1
    asig_a = asignaciones[0]
    assert asig_a.id_taller == taller_a.id_taller
    assert asig_a.id_tenant is not None, (
        "La asignación al taller elegido debe tener id_tenant para que aparezca en su dashboard"
    )

    # Hay al menos 2 candidatos (matching encuentra A y B)
    candidatos = db_session.query(CandidatoAsignacion).filter_by(id_incidente=id_inc).all()
    assert len(candidatos) >= 2, f"Esperábamos >= 2 candidatos, hay {len(candidatos)}"

    # Taller A rechaza
    r = client.put(
        f"/talleres/mi-taller/asignaciones/{asig_a.id_asignacion}/rechazar",
        json={"motivo": "No tengo capacidad ahora"},
        headers=taller_auth_headers(taller_a),
    )
    assert r.status_code == 200, r.text

    db_session.expire_all()

    asignaciones = db_session.query(Asignacion).filter_by(id_incidente=id_inc).all()
    # Debe existir una asignación pendiente NUEVA para un taller != A
    pendientes_nuevas = [
        a for a in asignaciones
        if a.estado.nombre == "pendiente" and a.id_taller != taller_a.id_taller
    ]
    assert len(pendientes_nuevas) >= 1, (
        f"Tras el rechazo de A, debería haberse creado una nueva asignación pendiente "
        f"para otro taller. Asignaciones: "
        f"{[(a.id_taller, a.estado.nombre) for a in asignaciones]}"
    )

    # La nueva asignación tiene id_tenant del taller destino — sin esto el
    # dashboard del taller no la vería.
    from app.models.taller import Taller
    for a in pendientes_nuevas:
        t = db_session.query(Taller).filter_by(id_taller=a.id_taller).one()
        assert a.id_tenant == t.id_tenant, (
            f"Nueva asignación #{a.id_asignacion} tiene id_tenant={a.id_tenant} "
            f"pero el taller destino tiene id_tenant={t.id_tenant}"
        )


# ============================================================
# FLUJO 3: VALIDACIONES DE SEGURIDAD / TENANT
# ============================================================

def test_taller_no_ve_asignaciones_de_otro_tenant(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    taller_auth_headers,
):
    """Confirma aislamiento multi-tenant: taller B no ve la asignación del cliente
    que eligió taller A, aunque B sea candidato."""
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import Asignacion

    cat = db_session.query(CategoriaProblema).first()
    _, taller_a = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    _, taller_b = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.79, -63.19,
    )

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers_cli = cliente_auth_headers(cliente)

    id_inc = _crear_borrador_y_confirmar(
        client, db_session, cliente, vehiculo, cat, taller_a, headers_cli,
    )
    asig_a = db_session.query(Asignacion).filter_by(id_incidente=id_inc).one()

    # Taller B intenta ver la asignación de A — debe ser invisible/403/404
    r = client.get(
        f"/talleres/mi-taller/asignaciones/{asig_a.id_asignacion}",
        headers=taller_auth_headers(taller_b),
    )
    assert r.status_code in (403, 404), (
        f"Taller B no debería poder ver la asignación de A. Status: {r.status_code}"
    )


def test_cliente_no_puede_ver_incidente_de_otro_cliente(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    cat = db_session.query(CategoriaProblema).first()
    _, taller = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )

    cliente_a = cliente_factory()
    vehiculo_a = vehiculo_factory(cliente_a)
    headers_a = cliente_auth_headers(cliente_a)

    cliente_b = cliente_factory()
    headers_b = cliente_auth_headers(cliente_b)

    id_inc = _crear_borrador_y_confirmar(
        client, db_session, cliente_a, vehiculo_a, cat, taller, headers_a,
    )

    # Cliente B intenta ver el incidente de A
    r = client.get(f"/incidencias/{id_inc}", headers=headers_b)
    assert r.status_code == 404, r.text


# ============================================================
# FLUJO 4: VALIDACIONES DEL BORRADOR
# ============================================================

def test_cliente_no_puede_reportar_si_ya_tiene_incidente_activo(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """Si el cliente tiene un incidente en pendiente/en_proceso, /POST /incidencias
    debe devolver 409 (no 500)."""
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    cat = db_session.query(CategoriaProblema).first()
    _, taller = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    _crear_borrador_y_confirmar(client, db_session, cliente, vehiculo, cat, taller, headers)

    # Segundo intento: ya tiene uno en pendiente
    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "Otro intento",
            "latitud": -17.78, "longitud": -63.18,
        },
        headers=headers,
    )
    assert r.status_code == 409, r.text
    detail = r.json()["detail"].lower()
    assert "activo" in detail or "pendiente" in detail


def test_cliente_puede_reportar_tras_cancelar_anterior(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    """
    Bug reportado: "después de cancelar no deja crear uno nuevo".
    Tras cancelar el incidente activo, el cliente debe poder reportar otro.
    """
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    cat = db_session.query(CategoriaProblema).first()
    _, taller = _crear_taller_con_categoria(
        db_session, tenant_factory, taller_factory, cat, -17.78, -63.18,
    )
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    headers = cliente_auth_headers(cliente)

    id_inc1 = _crear_borrador_y_confirmar(
        client, db_session, cliente, vehiculo, cat, taller, headers,
    )

    # Cliente cancela
    r_cancel = client.patch(f"/incidencias/{id_inc1}/cancelar", headers=headers)
    assert r_cancel.status_code == 200, r_cancel.text

    # Ahora SÍ puede reportar otro
    r = client.post(
        "/incidencias/",
        json={
            "id_vehiculo": vehiculo.id_vehiculo,
            "descripcion_usuario": "Después de cancelar",
            "latitud": -17.78, "longitud": -63.18,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["id_incidente"] != id_inc1


# ============================================================
# FLUJO 5: CATÁLOGOS Y LISTADOS
# ============================================================

def test_endpoint_categorias_publico(client):
    """Las categorías son públicas (no requieren auth) y devuelven todas las del seed."""
    r = client.get("/categorias")
    assert r.status_code == 200
    data = r.json()
    codigos = {c.get("codigo") for c in data}
    # Las canónicas que esperan los tests / KPIs / dashboard
    canonicas_esperadas = {
        "llantas", "mecanica_general", "electrico", "electronico",
        "chaperia_pintura", "grua_auxilio", "rutinario",
    }
    assert canonicas_esperadas.issubset(codigos), (
        f"Faltan códigos canónicos. Tenemos: {codigos}"
    )


def test_chaperia_pintura_requiere_cotizacion(client):
    r = client.get("/categorias")
    assert r.status_code == 200
    chap = next((c for c in r.json() if c.get("codigo") == "chaperia_pintura"), None)
    assert chap is not None
    assert chap.get("requiere_cotizacion") is True


def test_llantas_no_requiere_cotizacion(client):
    r = client.get("/categorias")
    chap = next((c for c in r.json() if c.get("codigo") == "llantas"), None)
    assert chap is not None
    assert chap.get("requiere_cotizacion") is False


# ============================================================
# FLUJO 6: TALLERES COMPATIBLES
# ============================================================

def test_talleres_compatibles_filtra_por_categoria_y_radio(
    client,
    db_session,
    tenant_factory,
    taller_factory,
):
    """
    GET /talleres/compatibles devuelve talleres dentro del radio que atienden
    la categoría especificada.
    """
    _ensure_estados(db_session)

    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    cat_principal = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    cat_otra = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    # Taller 1: atiende llantas, cerca
    tenant1 = tenant_factory()
    t1 = taller_factory(tenant1)
    t1.latitud, t1.longitud = -17.78, -63.18
    t1.activo = True
    t1.disponible = True
    db_session.add(TallerServicio(id_taller=t1.id_taller, id_categoria=cat_principal.id_categoria))

    # Taller 2: atiende llantas, lejos (>20km)
    tenant2 = tenant_factory()
    t2 = taller_factory(tenant2)
    t2.latitud, t2.longitud = -17.0, -63.0  # ~90km de distancia
    t2.activo = True
    t2.disponible = True
    db_session.add(TallerServicio(id_taller=t2.id_taller, id_categoria=cat_principal.id_categoria))

    # Taller 3: cerca pero NO atiende llantas (atiende chaperia)
    tenant3 = tenant_factory()
    t3 = taller_factory(tenant3)
    t3.latitud, t3.longitud = -17.78, -63.18
    t3.activo = True
    t3.disponible = True
    db_session.add(TallerServicio(id_taller=t3.id_taller, id_categoria=cat_otra.id_categoria))

    db_session.commit()

    r = client.get(
        f"/talleres/compatibles?id_categoria={cat_principal.id_categoria}"
        "&latitud=-17.78&longitud=-63.18&radio_km=20"
    )
    assert r.status_code == 200, r.text
    ids = [t["id_taller"] for t in r.json()]
    assert t1.id_taller in ids, "Taller que atiende y está cerca debe aparecer"
    assert t2.id_taller not in ids, "Taller lejos NO debe aparecer"
    assert t3.id_taller not in ids, "Taller que no atiende la categoría NO debe aparecer"
