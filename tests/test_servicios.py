"""Tests de servicios extendidos (F1)."""


def test_listar_categorias_devuelve_las_7_oficiales(client):
    r = client.get("/categorias")
    assert r.status_code == 200
    codigos = {c["codigo"] for c in r.json() if c["codigo"]}
    esperadas = {
        "llantas",
        "mecanica_general",
        "electrico",
        "electronico",
        "chaperia_pintura",
        "grua_auxilio",
        "rutinario",
    }
    assert esperadas.issubset(codigos)


def test_chaperia_requiere_cotizacion(client):
    r = client.get("/categorias")
    chap = next(c for c in r.json() if c["codigo"] == "chaperia_pintura")
    assert chap["requiere_cotizacion"] is True


def test_llantas_no_requiere_cotizacion(client):
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

    taller_llantas.latitud, taller_llantas.longitud = -16.5, -68.15
    taller_chaperia.latitud, taller_chaperia.longitud = -16.5, -68.15
    db_session.commit()

    cat_llantas = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    cat_chap = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    db_session.add_all(
        [
            TallerServicio(id_taller=taller_llantas.id_taller, id_categoria=cat_llantas.id_categoria),
            TallerServicio(id_taller=taller_chaperia.id_taller, id_categoria=cat_chap.id_categoria),
        ]
    )
    db_session.commit()

    r = client.get(
        "/talleres/compatibles",
        params={"id_categoria": cat_llantas.id_categoria, "latitud": -16.5, "longitud": -68.15},
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
    taller_lejos.latitud, taller_lejos.longitud = -17.7833, -63.1821
    db_session.commit()

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    db_session.add(TallerServicio(id_taller=taller_lejos.id_taller, id_categoria=cat.id_categoria))
    db_session.commit()

    r = client.get(
        "/talleres/compatibles",
        params={
            "id_categoria": cat.id_categoria,
            "latitud": -16.5,
            "longitud": -68.15,
            "radio_km": 50,
        },
    )
    assert r.status_code == 200
    ids = {t["id_taller"] for t in r.json()}
    assert taller_lejos.id_taller not in ids
