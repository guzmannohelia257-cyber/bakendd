"""Tests del flujo de cotizacion (F2)."""
from datetime import datetime, timezone, timedelta


def _crear_incidente_categoria(db_session, usuario, vehiculo, categoria, lat=-16.5, lng=-68.15):
    from app.models.catalogos import EstadoIncidente
    from app.models.incidente import Incidente

    estado = db_session.query(EstadoIncidente).first()
    inc = Incidente(
        id_usuario=usuario.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=estado.id_estado,
        id_categoria=categoria.id_categoria,
        latitud=lat,
        longitud=lng,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc


def test_solicitar_cotizaciones_invita_a_3_talleres(
    client, db_session, tenant_factory, taller_factory, cliente_factory, vehiculo_factory, cliente_auth_headers
):
    from app.models.catalogos import CategoriaProblema
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    talleres = []
    for _ in range(3):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        talleres.append(taller)
        db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria, tarifa_base=200))
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    headers = cliente_auth_headers(cliente)
    r = client.post(
        f"/incidentes/{incidente.id_incidente}/cotizaciones/solicitar",
        json={"radio_km": 50, "max_talleres": 3, "validez_horas": 2},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["invitadas"] == 3
    assert len(data["cotizaciones"]) == 3


def test_no_cotizar_categoria_directa(client, db_session, cliente_factory, vehiculo_factory, cliente_auth_headers):
    """Categoria 'llantas' no requiere cotizacion -> 400."""
    from app.models.catalogos import CategoriaProblema

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    headers = cliente_auth_headers(cliente)
    r = client.post(
        f"/incidentes/{incidente.id_incidente}/cotizaciones/solicitar",
        json={"radio_km": 50, "max_talleres": 3, "validez_horas": 2},
        headers=headers,
    )
    assert r.status_code == 400


def test_taller_responde_cotizacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
    cliente_factory,
    vehiculo_factory,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()
    pendiente = db_session.query(EstadoCotizacion).filter_by(nombre="pendiente").one()

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    taller.latitud, taller.longitud = -16.5, -68.15
    db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    cot = Cotizacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_cotizacion=pendiente.id_estado_cotizacion,
    )
    db_session.add(cot)
    db_session.commit()
    db_session.refresh(cot)

    headers = taller_auth_headers(taller)
    r = client.post(
        f"/cotizaciones/{cot.id_cotizacion}/responder",
        json={"monto_servicio": 500, "monto_repuestos": 200, "garantia_dias": 30, "nota": "Incluye lijado"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["monto_servicio"] == 500
    assert data["monto_repuestos"] == 200


def test_aceptar_cotizacion_rechaza_otras_y_crea_asignacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion, EstadoCotizacion
    from app.models.incidente import Asignacion

    cat = db_session.query(CategoriaProblema).filter_by(codigo="mecanica_general").one()
    enviada = db_session.query(EstadoCotizacion).filter_by(nombre="enviada").one()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = _crear_incidente_categoria(db_session, cliente, vehiculo, cat)

    cots = []
    for _ in range(2):
        t = tenant_factory()
        taller = taller_factory(t)
        cot = Cotizacion(
            id_tenant=t.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_estado_cotizacion=enviada.id_estado_cotizacion,
            monto_servicio=300,
            monto_repuestos=100,
            garantia_dias=15,
        )
        db_session.add(cot)
        cots.append(cot)
    db_session.commit()
    for c in cots:
        db_session.refresh(c)

    headers = cliente_auth_headers(cliente)
    elegida = cots[0]
    r = client.post(f"/cotizaciones/{elegida.id_cotizacion}/aceptar", headers=headers)
    assert r.status_code == 200, r.text

    db_session.refresh(elegida)
    db_session.refresh(cots[1])
    assert elegida.estado.nombre == "aceptada"
    assert cots[1].estado.nombre == "rechazada"

    asig = db_session.query(Asignacion).filter_by(id_incidente=incidente.id_incidente).first()
    assert asig is not None
    assert asig.id_taller == elegida.id_taller
