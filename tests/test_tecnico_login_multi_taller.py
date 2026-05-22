"""
Tests del flujo M9: login del tecnico contra un taller especifico,
seleccion de taller pre-login y cambio de taller activo.

Cubre:
  - GET /tecnicos/talleres-publicos (publico)
  - POST /tecnicos/login (con id_taller)
  - POST /tecnicos/me/cambiar-taller/{id_taller}
  - Fix POST /me/ubicacion con current_tenant.get()
"""
import uuid

import pytest

from app.core.security import create_access_token, hash_password
from app.models.taller import Taller
from app.models.usuario import Usuario
from app.models.usuario_taller import UsuarioTaller


# ============================================================
# Helpers
# ============================================================

def _crear_tecnico(db_session, *, password: str = "tec12345") -> Usuario:
    u = Usuario(
        id_rol=3,
        nombre=f"Tec {uuid.uuid4().hex[:4]}",
        email=f"tec-{uuid.uuid4().hex[:6]}@m9.example.com",
        password_hash=hash_password(password),
        activo=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _vincular(db_session, tecnico, taller, activo=True) -> UsuarioTaller:
    v = UsuarioTaller(
        id_usuario=tecnico.id_usuario,
        id_taller=taller.id_taller,
        activo=activo,
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


def _token_tecnico(tecnico: Usuario, taller: Taller | None = None) -> dict:
    """Helper para emitir token (con o sin tenant)."""
    extra = None
    if taller is not None:
        extra = {"id_tenant": taller.id_tenant, "id_taller_activo": taller.id_taller}
    token = create_access_token(subject_id=tecnico.id_usuario, tipo="usuario", extra_claims=extra)
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# GET /tecnicos/talleres-publicos
# ============================================================

def test_talleres_publicos_es_publico_y_lista_activos(
    client, db_session, tenant_factory, taller_factory,
):
    """Sin auth, devuelve solo talleres activos."""
    tenant = tenant_factory()
    taller_activo = taller_factory(tenant)
    taller_activo.activo = True
    taller_inactivo = taller_factory(tenant)
    taller_inactivo.activo = False
    db_session.commit()

    r = client.get("/tecnicos/talleres-publicos")
    assert r.status_code == 200

    ids = {t["id_taller"] for t in r.json()}
    assert taller_activo.id_taller in ids
    assert taller_inactivo.id_taller not in ids


def test_talleres_publicos_no_expone_password_hash(client, db_session, tenant_factory, taller_factory):
    """La respuesta NO debe contener campos sensibles."""
    tenant = tenant_factory()
    taller_factory(tenant)

    r = client.get("/tecnicos/talleres-publicos")
    assert r.status_code == 200
    for t in r.json():
        assert "password_hash" not in t
        assert "email" not in t
        assert "push_token" not in t


# ============================================================
# POST /tecnicos/login
# ============================================================

def test_login_tecnico_exitoso_devuelve_token_con_tenant(
    client, db_session, tenant_factory, taller_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller)

    r = client.post("/tecnicos/login", json={
        "email": tecnico.email,
        "password": "tec12345",
        "id_taller": taller.id_taller,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["access_token"]
    assert data["taller_activo"]["id_taller"] == taller.id_taller
    assert data["taller_activo"]["id_tenant"] == tenant.id_tenant
    assert data["usuario"]["id_usuario"] == tecnico.id_usuario


def test_login_tecnico_password_incorrecto_401(
    client, db_session, tenant_factory, taller_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller)

    r = client.post("/tecnicos/login", json={
        "email": tecnico.email,
        "password": "wrong",
        "id_taller": taller.id_taller,
    })
    assert r.status_code == 401


def test_login_tecnico_email_inexistente_401(client, tenant_factory, taller_factory):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    r = client.post("/tecnicos/login", json={
        "email": "noexiste@m9.example.com",
        "password": "x",
        "id_taller": taller.id_taller,
    })
    assert r.status_code == 401


def test_login_tecnico_usuario_rol_cliente_403(
    client, db_session, tenant_factory, taller_factory, cliente_factory,
):
    """Un usuario rol=1 (cliente) no puede loguearse como tecnico."""
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()  # rol=1
    _vincular(db_session, cliente, taller)  # aunque tuviera vinculo, no es tecnico

    r = client.post("/tecnicos/login", json={
        "email": cliente.email,
        "password": "secret123",
        "id_taller": taller.id_taller,
    })
    assert r.status_code == 403
    assert "tecnico" in r.json()["detail"].lower()


def test_login_tecnico_sin_vinculo_a_ese_taller_403(
    client, db_session, tenant_factory, taller_factory,
):
    """Tecnico existe pero NO esta vinculado al taller indicado."""
    tenant = tenant_factory()
    taller_a = taller_factory(tenant)
    taller_b = taller_factory(tenant)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller_a)  # solo vinculado a A

    r = client.post("/tecnicos/login", json={
        "email": tecnico.email,
        "password": "tec12345",
        "id_taller": taller_b.id_taller,
    })
    assert r.status_code == 403


def test_login_tecnico_vinculo_inactivo_403(
    client, db_session, tenant_factory, taller_factory,
):
    """Si el vinculo existe pero activo=False, no permite login."""
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller, activo=False)

    r = client.post("/tecnicos/login", json={
        "email": tecnico.email,
        "password": "tec12345",
        "id_taller": taller.id_taller,
    })
    assert r.status_code == 403


# ============================================================
# Tecnico con multiples talleres
# ============================================================

def test_tecnico_con_2_talleres_puede_elegir_cada_uno(
    client, db_session, tenant_factory, taller_factory,
):
    """Un mismo tecnico vinculado a 2 talleres: cada login da token con tenant correcto."""
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_b = taller_factory(tenant_b)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller_a)
    _vincular(db_session, tecnico, taller_b)

    # Login en A
    ra = client.post("/tecnicos/login", json={
        "email": tecnico.email, "password": "tec12345",
        "id_taller": taller_a.id_taller,
    })
    assert ra.status_code == 200
    assert ra.json()["taller_activo"]["id_tenant"] == tenant_a.id_tenant

    # Login en B (con mismo usuario)
    rb = client.post("/tecnicos/login", json={
        "email": tecnico.email, "password": "tec12345",
        "id_taller": taller_b.id_taller,
    })
    assert rb.status_code == 200
    assert rb.json()["taller_activo"]["id_tenant"] == tenant_b.id_tenant


# ============================================================
# POST /tecnicos/me/cambiar-taller/{id_taller}
# ============================================================

def test_cambiar_taller_activo_emite_nuevo_token(
    client, db_session, tenant_factory, taller_factory,
):
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_b = taller_factory(tenant_b)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller_a)
    _vincular(db_session, tecnico, taller_b)

    # Logueado en A
    headers_a = _token_tecnico(tecnico, taller_a)
    # Cambiar a B
    r = client.post(f"/tecnicos/me/cambiar-taller/{taller_b.id_taller}", headers=headers_a)
    assert r.status_code == 200, r.text
    assert r.json()["taller_activo"]["id_tenant"] == tenant_b.id_tenant


def test_cambiar_taller_sin_vinculo_404(
    client, db_session, tenant_factory, taller_factory,
):
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_b = taller_factory(tenant_b)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller_a)
    # NO vinculado a taller_b

    headers = _token_tecnico(tecnico, taller_a)
    r = client.post(f"/tecnicos/me/cambiar-taller/{taller_b.id_taller}", headers=headers)
    assert r.status_code == 404


def test_cambiar_taller_solo_tecnico_no_cliente(
    client, db_session, cliente_factory, cliente_auth_headers, tenant_factory, taller_factory,
):
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    cliente = cliente_factory()

    r = client.post(
        f"/tecnicos/me/cambiar-taller/{taller.id_taller}",
        headers=cliente_auth_headers(cliente),
    )
    assert r.status_code == 403


# ============================================================
# Fix /me/ubicacion: usar current_tenant del token
# ============================================================

def test_ubicacion_token_sin_tenant_responde_400(
    client, db_session, tenant_factory, taller_factory,
):
    """Si el tecnico vino del login viejo (sin id_tenant en JWT), responde 400 claro."""
    tenant = tenant_factory()
    taller = taller_factory(tenant)
    tecnico = _crear_tecnico(db_session)
    _vincular(db_session, tecnico, taller)

    headers = _token_tecnico(tecnico, taller=None)  # token sin tenant
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={"latitud": -16.5, "longitud": -68.15},
        headers=headers,
    )
    assert r.status_code == 400
    assert "id_tenant" in r.json()["detail"] or "tenant" in r.json()["detail"].lower()


def test_ubicacion_usa_taller_del_token_no_first(
    client, db_session, tenant_factory, taller_factory,
):
    """
    Tecnico vinculado a 2 talleres. Token apunta a tenant_b.
    El registro de ubicacion DEBE ir al vinculo de B, no al primero arbitrario.
    """
    tenant_a = tenant_factory()
    tenant_b = tenant_factory()
    taller_a = taller_factory(tenant_a)
    taller_b = taller_factory(tenant_b)
    tecnico = _crear_tecnico(db_session)
    vinculo_a = _vincular(db_session, tecnico, taller_a)
    vinculo_b = _vincular(db_session, tecnico, taller_b)

    headers = _token_tecnico(tecnico, taller_b)  # token con tenant B
    r = client.post(
        "/tecnicos/me/ubicacion",
        json={"latitud": -16.5, "longitud": -68.15},
        headers=headers,
    )
    assert r.status_code == 200

    # Refrescar y verificar: B fue actualizado, A NO
    db_session.refresh(vinculo_a)
    db_session.refresh(vinculo_b)
    assert vinculo_b.latitud == -16.5 and vinculo_b.longitud == -68.15
    # A no se actualizo
    assert vinculo_a.latitud is None or vinculo_a.latitud != -16.5
