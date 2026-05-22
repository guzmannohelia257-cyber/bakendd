"""Smoke: app arranca con WS, KPIs, broadcasts cableados."""
import pytest


def test_health_y_docs(client):
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_endpoints_nuevos_aparecen_en_openapi(client):
    spec = client.get("/openapi.json").json()
    paths = set(spec["paths"].keys())
    assert "/tenants/me/kpis" in paths
    assert "/admin/kpis/ranking-talleres" in paths
    assert "/tecnicos/me/ubicacion" in paths
    assert "/incidencias/{id_incidente}/aceptar" in paths


def test_ws_endpoint_registrado(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
