"""
E2E del ciclo 1:
  Cliente reporta incidente (chaperia)
   -> solicita cotizaciones a 3 talleres
   -> cada taller responde con precio
   -> cliente acepta la mas barata
   -> se crea Asignacion
   -> cliente cancela despues de aceptar
   -> se calcula compensacion 50%
"""


def test_flujo_completo_cotizacion_y_cancelacion(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    cliente_auth_headers,
    taller_auth_headers,
):
    from app.models.catalogos import CategoriaProblema
    from app.models.cotizacion import Cotizacion
    from app.models.taller import TallerServicio

    cat = db_session.query(CategoriaProblema).filter_by(codigo="chaperia_pintura").one()

    talleres = []
    for i in range(3):
        t = tenant_factory()
        taller = taller_factory(t)
        taller.latitud, taller.longitud = -16.5, -68.15
        taller.tarifa_traslado = 20
        db_session.add(
            TallerServicio(
                id_taller=taller.id_taller,
                id_categoria=cat.id_categoria,
                tarifa_base=300 + i * 50,
            )
        )
        talleres.append(taller)
    db_session.commit()

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    incidente = incidente_factory(cliente, vehiculo, categoria_codigo="chaperia_pintura")
    cli_h = cliente_auth_headers(cliente)

    r = client.post(
        f"/incidentes/{incidente.id_incidente}/cotizaciones/solicitar",
        json={"radio_km": 50, "max_talleres": 3, "validez_horas": 2},
        headers=cli_h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["invitadas"] == 3

    cotizaciones = (
        db_session.query(Cotizacion)
        .filter_by(id_incidente=incidente.id_incidente)
        .all()
    )
    assert len(cotizaciones) == 3

    precios_por_taller = {}
    for i, cot in enumerate(cotizaciones):
        taller = next(t for t in talleres if t.id_taller == cot.id_taller)
        precio_servicio = 200 + i * 100
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

    r = client.get(f"/incidentes/{incidente.id_incidente}/cotizaciones", headers=cli_h)
    assert r.status_code == 200
    recibidas = r.json()
    assert len(recibidas) == 3
    assert all(c["monto_servicio"] is not None for c in recibidas)

    mas_barata = min(recibidas, key=lambda c: c["monto_servicio"])
    r = client.post(f"/cotizaciones/{mas_barata['id_cotizacion']}/aceptar", headers=cli_h)
    assert r.status_code == 200
    id_asig = r.json()["id_asignacion"]
    taller_ganador_id = r.json()["id_taller"]
    assert precios_por_taller[taller_ganador_id] == 200

    # Invalidar cache: el endpoint modifico id_estado_cotizacion pero NO la
    # relacion `cot.estado` (cacheada en Identity Map). expire_all fuerza el
    # re-fetch de la relacion al acceder a .estado.nombre.
    db_session.expire_all()
    rechazadas = [
        c
        for c in db_session.query(Cotizacion).filter_by(id_incidente=incidente.id_incidente).all()
        if c.estado.nombre == "rechazada"
    ]
    assert len(rechazadas) == 2

    r = client.post(
        f"/asignaciones/{id_asig}/cancelar",
        json={"motivo": "Llego el seguro, pago la mitad del traslado"},
        headers=cli_h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nuevo_estado"] == "cancelada"
    assert data["compensacion_monto"] == 10.0
    assert data["compensacion_pagada"] is False
