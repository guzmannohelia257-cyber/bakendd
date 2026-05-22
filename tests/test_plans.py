"""GET /plans publico devuelve los planes seed."""


def test_listar_planes_publico(client):
    r = client.get("/plans")
    assert r.status_code == 200
    data = r.json()
    codigos = {p["codigo"] for p in data}
    assert {"free", "pro", "enterprise"}.issubset(codigos)


def test_plan_free_tiene_limites_correctos(client):
    r = client.get("/plans")
    free = next(p for p in r.json() if p["codigo"] == "free")
    assert free["precio_mensual"] == 0
    assert free["max_talleres"] == 1
    assert free["feature_websockets"] is False
    assert free["feature_reportes_ia"] is False


def test_plan_enterprise_tiene_features_premium(client):
    r = client.get("/plans")
    ent = next(p for p in r.json() if p["codigo"] == "enterprise")
    assert ent["feature_websockets"] is True
    assert ent["feature_kpis_avanzados"] is True
    assert ent["feature_reportes_ia"] is True
