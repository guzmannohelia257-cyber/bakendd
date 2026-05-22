"""Tests del flujo broadcast + first-accept-wins."""
import asyncio

from app.core.security import create_access_token


def _token(taller):
    extra = {"id_tenant": taller.id_tenant} if taller.id_tenant else None
    return create_access_token(subject_id=taller.id_taller, tipo="taller", extra_claims=extra)


def test_aceptar_emergencia_crea_asignacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import Asignacion, CandidatoAsignacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    db_session.add(
        CandidatoAsignacion(
            id_incidente=inc.id_incidente, id_taller=taller.id_taller, distancia_km=0.5
        )
    )
    db_session.commit()

    r = client.post(
        f"/incidencias/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 200, r.text
    assert r.json()["nuevo_estado"] == "aceptada"

    asig = db_session.query(Asignacion).filter_by(id_incidente=inc.id_incidente).first()
    assert asig is not None
    assert asig.id_taller == taller.id_taller


def test_segundo_taller_que_acepta_recibe_409(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.incidente import CandidatoAsignacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    talleres = []
    for _ in range(2):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))
        talleres.append(taller)
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    for t in talleres:
        db_session.add(
            CandidatoAsignacion(
                id_incidente=inc.id_incidente, id_taller=t.id_taller, distancia_km=0.5
            )
        )
    db_session.commit()

    r1 = client.post(
        f"/incidencias/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[0]),
    )
    assert r1.status_code == 200

    r2 = client.post(
        f"/incidencias/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[1]),
    )
    assert r2.status_code == 409


def test_taller_no_candidato_no_puede_aceptar(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    taller_auth_headers,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    r = client.post(
        f"/incidencias/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(taller),
    )
    assert r.status_code == 403


def test_ws_taller_recibe_evento_incidente_nuevo(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    """
    Verifica end-to-end: cliente crea incidente -> taller compatible recibe
    evento por WS.
    """
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio
    from app.services.broadcast_service import broadcast_emergencia

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")

    token = _token(taller)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        asyncio.run(broadcast_emergencia(inc, [taller]))
        msg = ws.receive_json()
        assert msg["event"] == "incidente.nuevo"
        assert msg["data"]["id_incidente"] == inc.id_incidente
