"""Tests del calculo de KPIs."""
from datetime import datetime, timedelta, timezone


def _now():
    return datetime.now(timezone.utc)


def test_kpi_resumen_endpoint(client, db_session, tenant_factory, taller_factory, taller_auth_headers):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "tiempo_promedio_asignacion_min" in data
    assert "incidentes_por_categoria" in data
    assert isinstance(data["incidentes_por_categoria"], list)


def test_kpi_incidentes_por_categoria_agrupa(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    for _ in range(3):
        inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")
        inc.id_tenant = tenant.id_tenant
    incidente_factory(cliente, vehiculo, categoria_codigo="chaperia_pintura").id_tenant = tenant.id_tenant
    db_session.commit()

    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller))
    cats = {c["codigo"]: c["total"] for c in r.json()["incidentes_por_categoria"]}
    assert cats.get("llantas") == 3
    assert cats.get("chaperia_pintura") == 1


def test_kpi_tiempo_asignacion_calcula(
    db_session,
    tenant_factory,
    taller_factory,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion
    from app.services import kpi_service

    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)
    inc = incidente_factory(cliente, vehiculo)
    inc.id_tenant = tenant.id_tenant
    db_session.commit()

    estado_aceptada = db_session.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
    asig = Asignacion(
        id_tenant=tenant.id_tenant,
        id_incidente=inc.id_incidente,
        id_taller=taller.id_taller,
        id_estado_asignacion=estado_aceptada.id_estado_asignacion,
    )
    db_session.add(asig)
    db_session.commit()

    from sqlalchemy import text
    db_session.execute(
        text("UPDATE incidente SET created_at = NOW() - INTERVAL '10 minutes' WHERE id_incidente = :i"),
        {"i": inc.id_incidente},
    )
    db_session.commit()

    promedio = kpi_service.tiempo_promedio_asignacion_min(
        db_session, _now() - timedelta(hours=1), _now(), id_tenant=tenant.id_tenant
    )
    assert promedio >= 9 and promedio <= 11


def test_ranking_talleres_super_admin(client, db_session, admin_headers, tenant_factory, taller_factory):
    tenant = tenant_factory()
    taller_factory(tenant)
    r = client.get("/admin/kpis/ranking-talleres", headers=admin_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_kpi_aisla_por_tenant(
    client,
    db_session,
    tenant_factory,
    taller_factory,
    taller_auth_headers,
    cliente_factory,
    vehiculo_factory,
    incidente_factory,
):
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_factory(tenant_b)

    cliente = cliente_factory()
    vehiculo = vehiculo_factory(cliente)

    for _ in range(2):
        inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")
        inc.id_tenant = tenant_b.id_tenant
    inc = incidente_factory(cliente, vehiculo, categoria_codigo="llantas")
    inc.id_tenant = tenant_a.id_tenant
    db_session.commit()

    r = client.get("/tenants/me/kpis", headers=taller_auth_headers(taller_a))
    cats = {c["codigo"]: c["total"] for c in r.json()["incidentes_por_categoria"]}
    assert cats.get("llantas") == 1
