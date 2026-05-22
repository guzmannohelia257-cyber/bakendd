"""Tests de cancelacion con compensacion (F3)."""


def _crear_asignacion(db_session, tenant, taller, incidente, estado_nombre, tarifa_traslado=10):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    estado = db_session.query(EstadoAsignacion).filter_by(nombre=estado_nombre).first()
    if not estado:
        estado = EstadoAsignacion(nombre=estado_nombre)
        db_session.add(estado)
        db_session.commit()
        db_session.refresh(estado)

    taller.tarifa_traslado = tarifa_traslado
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=incidente.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado.id_estado_asignacion,
    )
    db_session.add(asig)
    db_session.commit()
    db_session.refresh(asig)
    return asig


def test_cancelar_pendiente_compensacion_cero(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "pendiente", tarifa_traslado=20)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Me ayudo un vecino"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["compensacion_monto"] == 0.0
    assert data["compensacion_pagada"] is True
    assert data["nuevo_estado"] == "cancelada"


def test_cancelar_aceptada_compensacion_50pct(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "aceptada", tarifa_traslado=20)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Llego el seguro"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text
    assert r.json()["compensacion_monto"] == 10.0


def test_cancelar_en_camino_compensacion_100pct(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "en_camino", tarifa_traslado=20)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Cambio de planes"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200
    assert r.json()["compensacion_monto"] == 20.0


def test_no_se_puede_cancelar_completada(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "completada")

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "No aplica"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 409


def test_solo_dueno_puede_cancelar(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    dueno = cliente_factory()
    intruso = cliente_factory()
    vehiculo = vehiculo_factory(dueno)
    inc = incidente_factory(dueno, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "aceptada")

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Soy un atacante"},
        headers=cliente_auth_headers(intruso),
    )
    assert r.status_code == 403


def test_cancelacion_crea_pago_pendiente_de_compensacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    incidente_factory,
):
    from app.models.transaccional import Pago

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    asig = _crear_asignacion(db_session, tenant, taller, inc, "en_camino", tarifa_traslado=30)

    r = client.post(
        f"/asignaciones/{asig.id_asignacion}/cancelar",
        json={"motivo": "Test compensacion"},
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 200, r.text

    pago = db_session.query(Pago).filter_by(id_incidente=inc.id_incidente).first()
    assert pago is not None
    assert float(pago.monto_total) == 30.0
    assert float(pago.comision_plataforma) == 3.0
    assert float(pago.monto_taller) == 27.0
