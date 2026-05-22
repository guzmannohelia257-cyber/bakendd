"""
E2E Ciclo 2: cliente reporta -> broadcast a talleres ->
primero acepta -> tracking GPS -> geofencing llegado.
"""


def test_flujo_completo_emergencia_tiempo_real(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    tecnico_factory,
    cliente_factory,
    vehiculo_factory,
    cliente_auth_headers,
    taller_auth_headers,
    tecnico_auth_headers,
):
    from app.models.catalogos import CategoriaProblema, EstadoAsignacion, EstadoIncidente
    from app.models.incidente import CandidatoAsignacion, Incidente
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="llantas").one()
    talleres = []
    for _ in range(3):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        db_session.add(TallerServicio(id_taller=taller.id_taller, id_categoria=cat.id_categoria))
        talleres.append(taller)
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    estado_pendiente = db_session.query(EstadoIncidente).first()
    inc = Incidente(
        id_usuario=cliente.id_usuario,
        id_vehiculo=vehiculo.id_vehiculo,
        id_estado=estado_pendiente.id_estado,
        id_categoria=cat.id_categoria,
        latitud=-16.5005,
        longitud=-68.1505,
        descripcion_usuario="Se me pincho la llanta",
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    for t in talleres:
        db_session.add(
            CandidatoAsignacion(
                id_incidente=inc.id_incidente,
                id_taller=t.id_taller,
                distancia_km=0.1,
            )
        )
    db_session.commit()

    r = client.post(
        f"/incidencias/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[0]),
    )
    assert r.status_code == 200
    id_asig = r.json()["id_asignacion"]

    r2 = client.post(
        f"/incidencias/{inc.id_incidente}/aceptar",
        headers=taller_auth_headers(talleres[1]),
    )
    assert r2.status_code == 409

    tecnico = tecnico_factory(talleres[0])
    from sqlalchemy import text
    db_session.execute(
        text("UPDATE asignacion SET id_usuario = :u WHERE id_asignacion = :a"),
        {"u": tecnico.id_usuario, "a": id_asig},
    )
    db_session.commit()

    r3 = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.510,
            "longitud": -68.160,
            "id_asignacion": id_asig,
        },
        headers=tecnico_auth_headers(tecnico, talleres[0]),
    )
    assert r3.status_code == 200
    assert r3.json()["llegado_auto"] is False
    assert r3.json()["eta"]["distancia_km"] > 0

    if not db_session.query(EstadoAsignacion).filter_by(nombre="llegado").first():
        db_session.add(EstadoAsignacion(nombre="llegado"))
        db_session.commit()

    r4 = client.post(
        "/tecnicos/me/ubicacion",
        json={
            "latitud": -16.5005,
            "longitud": -68.1505,
            "id_asignacion": id_asig,
        },
        headers=tecnico_auth_headers(tecnico, talleres[0]),
    )
    assert r4.status_code == 200
    assert r4.json()["llegado_auto"] is True
