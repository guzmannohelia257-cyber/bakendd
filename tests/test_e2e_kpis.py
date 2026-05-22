"""Verifica que despues del flujo E2E, los KPIs reflejan la actividad."""


def test_kpis_aparecen_tras_actividad(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
    asignacion_factory,
    taller_auth_headers,
):
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
