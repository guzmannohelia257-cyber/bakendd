"""Tests para POST /signup (onboarding self-service)."""
import uuid


def _signup_payload(slug_suffix: str | None = None) -> dict:
    slug = f"acme-{slug_suffix or uuid.uuid4().hex[:6]}"
    return {
        "tenant_slug": slug,
        "tenant_nombre": "Acme Corp",
        "taller_nombre": "Acme Taller Central",
        "taller_email": f"{slug}@acme.example.com",
        "taller_password": "supersecret123",
        "taller_telefono": "+591 70000000",
        "plan_codigo": "free",
    }


def test_signup_crea_tenant_y_taller_y_token(client):
    payload = _signup_payload()
    r = client.post("/signup", json=payload)
    assert r.status_code == 201, r.text

    data = r.json()
    assert data["tenant"]["slug"] == payload["tenant_slug"]
    assert data["tenant"]["nombre"] == payload["tenant_nombre"]
    assert data["taller_email"] == payload["taller_email"]
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["id_taller"] > 0


def test_signup_token_funciona_para_endpoints_protegidos(client):
    payload = _signup_payload()
    r = client.post("/signup", json=payload)
    token = r.json()["access_token"]

    me = client.get("/tenants/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["slug"] == payload["tenant_slug"]


def test_signup_rechaza_slug_duplicado(client):
    payload = _signup_payload(slug_suffix="dup")
    r1 = client.post("/signup", json=payload)
    assert r1.status_code == 201

    # Mismo slug, distinto email
    payload2 = dict(payload)
    payload2["taller_email"] = f"otro-{uuid.uuid4().hex[:4]}@acme.example.com"
    r2 = client.post("/signup", json=payload2)
    assert r2.status_code == 409
    assert "slug" in r2.json()["detail"].lower()


def test_signup_rechaza_email_taller_duplicado(client):
    payload = _signup_payload(slug_suffix="emaildup")
    r1 = client.post("/signup", json=payload)
    assert r1.status_code == 201

    # Distinto slug, mismo email
    payload2 = dict(payload)
    payload2["tenant_slug"] = f"otro-{uuid.uuid4().hex[:6]}"
    r2 = client.post("/signup", json=payload2)
    assert r2.status_code == 409
    assert "email" in r2.json()["detail"].lower()


def test_signup_rechaza_slug_invalido(client):
    payload = _signup_payload()
    payload["tenant_slug"] = "INVALID SLUG"  # mayusculas y espacio
    r = client.post("/signup", json=payload)
    assert r.status_code == 422


def test_signup_rechaza_password_corto(client):
    payload = _signup_payload()
    payload["taller_password"] = "short"
    r = client.post("/signup", json=payload)
    assert r.status_code == 422


def test_signup_rechaza_plan_inexistente(client):
    payload = _signup_payload()
    payload["plan_codigo"] = "no-existe"
    r = client.post("/signup", json=payload)
    assert r.status_code == 400
