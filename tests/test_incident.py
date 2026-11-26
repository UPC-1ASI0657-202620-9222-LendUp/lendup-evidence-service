from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.application.services import incident
from app.domain.entities.incident import IncidentType
from app.main import app
from app.shared.security import Principal


def test_incident_routes_require_authentication():
    client = TestClient(app)
    identifier = str(uuid4())
    assert client.get("/api/v1/incidencias").status_code == 401
    assert client.get(f"/api/v1/incidencias/{identifier}").status_code == 401
    assert client.post("/api/v1/incidencias", json={}).status_code == 401
    assert client.post(f"/api/v1/incidencias/{identifier}/descargo", json={"contenido": "a" * 20}).status_code == 401


def test_report_rejects_short_description(monkeypatch):
    monkeypatch.setattr(incident, "participant_loan", lambda *args: {"estado": "ACTIVO"})
    user = Principal("uid", str(uuid4()), "token")
    body = dict(prestamo_id=uuid4(), tipo=IncidentType.DAMAGE, descripcion="   corto   ")
    with pytest.raises(HTTPException) as error:
        incident.report(None, user, body, [])
    assert error.value.status_code == 400


def test_report_rejects_video(monkeypatch):
    monkeypatch.setattr(incident, "participant_loan", lambda *args: {"estado": "ACTIVO"})
    user = Principal("uid", str(uuid4()), "token")
    body = dict(prestamo_id=uuid4(), tipo=IncidentType.DAMAGE, descripcion="Descripción válida de daño")
    with pytest.raises(HTTPException) as error:
        incident.report(None, user, body, [b"0000ftyp0000"])
    assert error.value.status_code == 400


def test_incident_openapi_paths():
    paths = app.openapi()["paths"]
    assert set(paths["/api/v1/incidencias"]) >= {"get", "post"}
    assert "get" in paths["/api/v1/incidencias/{id}"]
    assert "post" in paths["/api/v1/incidencias/{id}/descargo"]
