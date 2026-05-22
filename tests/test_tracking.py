"""Tests de tracking + ETA."""
import asyncio


def _vincular_tecnico_a_taller(db_session, taller, hash_password_fn):
    """Crea usuario rol=3 vinculado al taller."""
    from app.models.usuario import Usuario
    from app.models.usuario_taller import UsuarioTaller
    import uuid

    u = Usuario(
        id_rol=3,
        nombre="Tecnico Test",
        email=f"tec-{uuid.uuid4().hex[:6]}@test.example.com",
        password_hash=hash_password_fn("tec12345"),
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    vin = UsuarioTaller(id_usuario=u.id_usuario, id_taller=taller.id_taller, activo=True)
    db_session.add(vin)
    db_session.commit()
    return u


def test_reportar_ubicacion_sin_asignacion_solo_actualiza_vinculo(
    client,
    db_session,
    tenant_factory,
    taller_factory,
):
    from app.core.security import hash_password, create_access_token
    from app.models.usuario_taller import UsuarioTaller

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _vincular_tecnico_a_taller(db_session, taller, hash_password)

    # M9: token DEBE incluir id_tenant del taller activo (post-login multi-taller)
    token = create_access_token(
        subject_id=tecnico.id_usuario,
        tipo="usuario",
        extra_claims={"id_tenant": tenant.id_tenant, "id_taller_activo": taller.id_taller},
    )
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={"latitud": -16.5, "longitud": -68.15},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    vin = (
        db_session.query(UsuarioTaller)
        .filter_by(id_usuario=tecnico.id_usuario)
        .first()
    )
    assert vin.latitud == -16.5
    assert vin.longitud == -68.15


def test_reportar_ubicacion_con_asignacion_inserta_historico_y_calcula_eta(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from app.core.security import hash_password, create_access_token
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion
    from app.models.ubicacion import UbicacionTecnico

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _vincular_tecnico_a_taller(db_session, taller, hash_password)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, lat=-16.500, lng=-68.150)

    estado_aceptada = db_session.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc.id_incidente,
        id_taller=taller.id_taller,
        id_usuario=tecnico.id_usuario,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db_session.add(asig)
    db_session.commit()
    db_session.refresh(asig)

    # M9: token DEBE incluir id_tenant del taller activo (post-login multi-taller)
    token = create_access_token(
        subject_id=tecnico.id_usuario,
        tipo="usuario",
        extra_claims={"id_tenant": tenant.id_tenant, "id_taller_activo": taller.id_taller},
    )
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.510,
            "longitud": -68.160,
            "id_asignacion": asig.id_asignacion,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["eta"]["distancia_km"] > 0

    hist = (
        db_session.query(UbicacionTecnico)
        .filter_by(id_asignacion=asig.id_asignacion)
        .all()
    )
    assert len(hist) == 1


def test_geofencing_marca_llegado_automatico(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from app.core.security import hash_password, create_access_token
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _vincular_tecnico_a_taller(db_session, taller, hash_password)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo, lat=-16.5000, lng=-68.1500)

    estado_aceptada = db_session.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc.id_incidente,
        id_taller=taller.id_taller,
        id_usuario=tecnico.id_usuario,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db_session.add(asig)
    db_session.commit()
    db_session.refresh(asig)

    if not db_session.query(EstadoAsignacion).filter_by(nombre="llegado").first():
        db_session.add(EstadoAsignacion(nombre="llegado"))
        db_session.commit()

    # M9: token DEBE incluir id_tenant del taller activo (post-login multi-taller)
    token = create_access_token(
        subject_id=tecnico.id_usuario,
        tipo="usuario",
        extra_claims={"id_tenant": tenant.id_tenant, "id_taller_activo": taller.id_taller},
    )
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.5000,
            "longitud": -68.1500,
            "id_asignacion": asig.id_asignacion,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["llegado_auto"] is True

    db_session.refresh(asig)
    assert asig.estado.nombre == "llegado"


def test_calcular_eta_funcion(monkeypatch):
    """Test unitario del helper de ETA con OSRM mockeado."""
    from app.services import tracking_service

    async def fake_failing_get(*args, **kwargs):
        raise Exception("OSRM down")

    monkeypatch.setattr("httpx.AsyncClient.get", fake_failing_get)

    d, eta = asyncio.run(tracking_service.calcular_eta(-16.5, -68.15, -16.6, -68.20))
    assert d > 0
    assert eta > 0
