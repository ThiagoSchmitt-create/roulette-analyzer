"""Smoke tests para api (FastAPI)."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from api import app


@pytest.fixture
def client():
    c = TestClient(app)
    # limpa estado entre testes
    yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_spin_and_history(client):
    wid = "test-spin-history"
    client.delete(f"/history/{wid}")
    for n in ("7", "17", "27", "0"):
        r = client.post("/spin", json={"wheel_id": wid, "wheel_type": "european", "number": n})
        assert r.status_code == 200
    h = client.get(f"/history/{wid}")
    assert h.status_code == 200
    assert h.json()["total"] == 4
    assert h.json()["last"] == ["7", "17", "27", "0"]


def test_invalid_number_rejected(client):
    r = client.post("/spin", json={"wheel_id": "x", "wheel_type": "european", "number": "37"})
    assert r.status_code == 400


def test_analyze_endpoint_returns_verdict(client):
    spins = ["7", "32", "15", "19", "4", "21", "2", "25"] * 10
    r = client.post("/analyze", json={"wheel": "european", "spins": spins, "run_simulation": False})
    assert r.status_code == 200
    body = r.json()
    assert "bias" in body
    assert body["bias"]["verdict"] in (
        "amostra_insuficiente", "inconclusivo", "indicio_fraco",
        "vies_provavel", "sem_vies_detectado",
    )


def test_report_404_when_no_history(client):
    r = client.get("/report/never-seen")
    assert r.status_code == 404
