from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.application.services import admin_incident
from app.domain.entities.incident import GuaranteeDecision
from app.domain.entities.resolution import money, remaining_guarantee, validate_decision
from app.main import app
from app.shared import security
from app.shared.security import Principal


def test_admin_routes_require_authentication():
    client = TestClient(app)
    identifier = str(uuid4())
    base = "/api/v1/admin/incidencias"
    assert client.get(base).status_code == 401
    assert client.post(f"{base}/{identifier}/revision").status_code == 401
    assert client.post(f"{base}/{identifier}/observaciones", json={"contenido": "nota"}).status_code == 401
    assert client.post(f"{base}/{identifier}/resolucion", json={"justificacion_resolucion": "a"*20, "decision_garantia": "SIN_AFECTACION"}).status_code == 401


def test_non_admin_rejected(monkeypatch):
    monkeypatch.setattr(security, "resolve_role", lambda _: "ESTUDIANTE")
    with pytest.raises(HTTPException) as error:
        security.current_admin(Principal("uid", str(uuid4()), "token"))
    assert error.value.status_code == 403


def test_authoritative_admin_allowed(monkeypatch):
    monkeypatch.setattr(security, "resolve_role", lambda _: "ADMINISTRADOR")
    user = Principal("uid", str(uuid4()), "token")
    assert security.current_admin(user) == user


def test_role_service_failure_not_bypassed(monkeypatch):
    def unavailable(_):
        raise HTTPException(503, "unavailable")
    monkeypatch.setattr(security, "resolve_role", unavailable)
    with pytest.raises(HTTPException) as error:
        security.current_admin(Principal("uid", str(uuid4()), "token"))
    assert error.value.status_code == 503


def test_guarantee_decisions():
    available = remaining_guarantee("100.00", "30.00")
    assert available == Decimal("70.00")
    assert validate_decision(GuaranteeDecision.NONE, "0", available) == 0
    assert validate_decision(GuaranteeDecision.PARTIAL, "25.50", available) == Decimal("25.50")
    assert validate_decision(GuaranteeDecision.TOTAL, "70", available) == available


def test_invalid_guarantee_decisions():
    for decision, amount, available in [
        (GuaranteeDecision.NONE, "1", "100"),
        (GuaranteeDecision.PARTIAL, "0", "100"),
        (GuaranteeDecision.PARTIAL, "100", "100"),
        (GuaranteeDecision.TOTAL, "101", "100"),
        (GuaranteeDecision.TOTAL, "0", "0"),
    ]:
        with pytest.raises(ValueError):
            validate_decision(decision, amount, available)
    for value in ["-1", "1.001", "NaN", "Infinity"]:
        with pytest.raises(ValueError):
            money(value)


def test_review_required():
    for state in ("PENDIENTE", "RESUELTA"):
        with pytest.raises(HTTPException) as error:
            admin_incident.require_review({"estado": state})
        assert error.value.status_code == 409
    admin_incident.require_review({"estado": "EN_REVISION"})


def test_review_is_idempotent(monkeypatch):
    row = {"id": str(uuid4()), "estado": "EN_REVISION"}
    session = Mock()
    monkeypatch.setattr(admin_incident, "locked_incident", lambda *args: row)
    monkeypatch.setattr(admin_incident, "local_detail", lambda session, incident: incident)
    change = Mock()
    monkeypatch.setattr(admin_incident, "change", change)
    assert admin_incident.review(session, uuid4()) == row
    change.assert_not_called()


def test_resolution_fails_closed_when_loans_unavailable(monkeypatch):
    row = {"id": str(uuid4()), "estado": "EN_REVISION", "prestamo_id": str(uuid4())}
    session = Mock()
    monkeypatch.setattr(admin_incident, "get_incident", lambda *args: row)
    def unavailable(_):
        raise HTTPException(503, "unavailable")
    monkeypatch.setattr(admin_incident, "administrative_loan", unavailable)
    with pytest.raises(HTTPException) as error:
        admin_incident.resolve(session, uuid4(), Principal("uid", str(uuid4()), "token"),
                               "Justificación de resolución válida", GuaranteeDecision.NONE, Decimal("0"))
    assert error.value.status_code == 503
    session.commit.assert_not_called()
