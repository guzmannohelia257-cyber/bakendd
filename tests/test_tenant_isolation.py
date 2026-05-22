"""
Tests del filtro multi-tenant: un tenant no puede ver datos de otro.
"""
from app.core.tenant_context import current_tenant
from app.models.incidente import Incidente


def test_filtro_aisla_incidentes_entre_tenants(
    db_session, tenant_factory, taller_factory
):
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()

    # Crear un incidente bajo tenant_a (directamente via SQL para no depender
    # de relaciones FK complicadas - usuario, vehiculo, estado, etc.)
    # Aprovechamos los catalogos/usuarios existentes en la BD de dev.
    from sqlalchemy import text

    inc_id_a = db_session.execute(
        text(
            """
            INSERT INTO incidente
                (id_tenant, id_usuario, id_vehiculo, id_estado, latitud, longitud)
            SELECT :tid,
                   (SELECT id_usuario FROM usuario ORDER BY id_usuario LIMIT 1),
                   (SELECT id_vehiculo FROM vehiculo ORDER BY id_vehiculo LIMIT 1),
                   (SELECT id_estado   FROM estado_incidente ORDER BY id_estado LIMIT 1),
                   -17.0, -67.0
            RETURNING id_incidente
            """
        ),
        {"tid": tenant_a.id_tenant},
    ).scalar_one()

    db_session.commit()

    # Sin contexto -> ve todo (incluido el nuevo)
    n_global = db_session.query(Incidente).filter(Incidente.id_incidente == inc_id_a).count()
    assert n_global == 1

    # Con contexto de tenant_a -> ve el incidente
    tok = current_tenant.set(tenant_a.id_tenant)
    try:
        n_a = db_session.query(Incidente).filter(Incidente.id_incidente == inc_id_a).count()
    finally:
        current_tenant.reset(tok)
    assert n_a == 1

    # Con contexto de tenant_b -> NO lo ve
    tok = current_tenant.set(tenant_b.id_tenant)
    try:
        n_b = db_session.query(Incidente).filter(Incidente.id_incidente == inc_id_a).count()
    finally:
        current_tenant.reset(tok)
    assert n_b == 0


def test_super_admin_ve_todo(db_session, tenant_factory):
    """tenant_id=0 es escape hatch."""
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()

    tok = current_tenant.set(0)
    try:
        # Ambos tenants deben ser visibles
        from app.models.tenant import Tenant
        slugs = [t.slug for t in db_session.query(Tenant).filter(
            Tenant.id_tenant.in_([tenant_a.id_tenant, tenant_b.id_tenant])
        ).all()]
    finally:
        current_tenant.reset(tok)
    assert len(slugs) == 2


def test_tenant_inexistente_no_ve_nada_con_id_tenant_not_null(db_session, tenant_factory):
    """
    Con include_legacy=False, un tenant_id que no corresponde a ningun dato
    no devuelve filas (no se incluyen los NULL).
    """
    tenant = tenant_factory()
    # Tenant que no tiene incidentes asociados
    tok = current_tenant.set(tenant.id_tenant)
    try:
        n = db_session.query(Incidente).count()
    finally:
        current_tenant.reset(tok)
    assert n == 0


def test_middleware_extrae_tenant_del_jwt(client, tenant_factory, taller_factory, taller_auth_headers):
    """
    Verifica que el middleware setea el contexto a partir del JWT.
    Lo comprobamos indirectamente: /tenants/me debe responder con el tenant del taller.
    """
    tenant = tenant_factory(slug_prefix="mw")
    taller = taller_factory(tenant)
    headers = taller_auth_headers(taller)
    r = client.get("/tenants/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["id_tenant"] == tenant.id_tenant
