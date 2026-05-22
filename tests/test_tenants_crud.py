"""CRUD de /tenants (super-admin + miembros)."""
import uuid


def test_listar_tenants_requiere_admin(client):
    r = client.get("/tenants")
    # Sin token -> 401
    assert r.status_code == 401


def test_listar_tenants_no_admin_es_403(client, taller_factory, tenant_factory, taller_auth_headers):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    headers = taller_auth_headers(taller)

    r = client.get("/tenants", headers=headers)
    # Token de taller (no de admin user) -> 401 porque get_current_user rechaza tipo=taller
    assert r.status_code in (401, 403)


def test_listar_tenants_como_admin(client, admin_headers, tenant_factory):
    tenant_factory(slug_prefix="visible")
    headers = admin_headers()
    r = client.get("/tenants", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert any(t["slug"].startswith("visible-") for t in data)


def test_crear_tenant_admin(client, admin_headers, db_session):
    headers = admin_headers()
    slug = f"new-{uuid.uuid4().hex[:6]}"
    payload = {
        "slug": slug,
        "nombre": "Nuevo Tenant",
        "email_contacto": f"{slug}@nuevo.example.com",
        "telefono": "+591 70000000",
    }
    r = client.post("/tenants", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["slug"] == slug
    assert data["nombre"] == "Nuevo Tenant"
    assert data["activo"] is True
    assert data["suspendido"] is False


def test_crear_tenant_rechaza_slug_duplicado(client, admin_headers, tenant_factory):
    existente = tenant_factory(slug_prefix="dup")
    headers = admin_headers()
    payload = {
        "slug": existente.slug,
        "nombre": "Otro",
        "email_contacto": "otro@dup.example.com",
    }
    r = client.post("/tenants", json=payload, headers=headers)
    assert r.status_code == 409


def test_mi_tenant_como_taller_autenticado(client, tenant_factory, taller_factory, taller_auth_headers):
    tenant = tenant_factory(slug_prefix="mio")
    taller = taller_factory(tenant)
    headers = taller_auth_headers(taller)

    r = client.get("/tenants/me", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["id_tenant"] == tenant.id_tenant


def test_actualizar_tenant_propio(client, tenant_factory, taller_factory, taller_auth_headers):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    headers = taller_auth_headers(taller)

    r = client.patch(
        f"/tenants/{tenant.id_tenant}",
        json={"nombre": "Nombre Actualizado"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["nombre"] == "Nombre Actualizado"


def test_no_puedo_actualizar_tenant_ajeno(client, tenant_factory, taller_factory, taller_auth_headers):
    mi_tenant = tenant_factory()
    otro_tenant = tenant_factory()
    taller_mio = taller_factory(mi_tenant)
    headers = taller_auth_headers(taller_mio)

    r = client.patch(
        f"/tenants/{otro_tenant.id_tenant}",
        json={"nombre": "Hackeado"},
        headers=headers,
    )
    assert r.status_code == 403


def test_vincular_taller_a_tenant_como_admin(
    client, admin_headers, tenant_factory, db_session, plan_free
):
    """
    Crea un taller huerfano (tras 0003 ya no es legal, pero el endpoint
    debe poder relinkear taller existente a otro tenant). Simulamos:
    creamos taller en tenant A y lo movemos a tenant B (debe fallar porque ya tiene tenant).
    """
    from app.models.taller import Taller
    from app.core.security import hash_password
    import uuid as _uuid

    tenant_a = tenant_factory()
    tenant_b = tenant_factory()

    taller = Taller(
        id_tenant=tenant_a.id_tenant,
        nombre="Taller A",
        email=f"link-{_uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("xxxxxxxx"),
    )
    db_session.add(taller)
    db_session.commit()
    db_session.refresh(taller)

    headers = admin_headers()
    r = client.post(
        f"/tenants/{tenant_b.id_tenant}/talleres/link",
        json={"id_taller": taller.id_taller},
        headers=headers,
    )
    # Ya pertenece a tenant_a -> 409
    assert r.status_code == 409


def test_vincular_taller_inexistente_404(client, admin_headers, tenant_factory):
    tenant = tenant_factory()
    headers = admin_headers()
    r = client.post(
        f"/tenants/{tenant.id_tenant}/talleres/link",
        json={"id_taller": 9999999},
        headers=headers,
    )
    assert r.status_code == 404


def test_get_suscripcion_propia(client, tenant_factory, taller_factory, taller_auth_headers, db_session, plan_free):
    tenant = tenant_factory()
    # Asignar suscripcion manual al tenant
    from app.models.tenant import Suscripcion
    sub = Suscripcion(id_tenant=tenant.id_tenant, id_plan=plan_free.id_plan, estado="activa")
    db_session.add(sub)
    db_session.commit()

    taller = taller_factory(tenant)
    headers = taller_auth_headers(taller)

    r = client.get(f"/tenants/{tenant.id_tenant}/suscripcion", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["id_plan"] == plan_free.id_plan
    assert r.json()["estado"] == "activa"
