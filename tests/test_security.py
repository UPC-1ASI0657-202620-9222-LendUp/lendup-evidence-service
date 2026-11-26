from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.shared import security


def test_verifies_revocation_and_email_before_resolving_identity(monkeypatch):
    firebase = object()
    verify = Mock(return_value={"uid": "uid", "email_verified": False})
    resolve = Mock(return_value=str(uuid4()))
    monkeypatch.setattr(security, "firebase_app", lambda: firebase)
    monkeypatch.setattr(security.auth, "verify_id_token", verify)
    monkeypatch.setattr(security, "resolve_user", resolve)
    client = TestClient(app)
    assert client.get("/api/v1/incidencias", headers={"Authorization": "Bearer fake"}).status_code == 403
    verify.assert_called_once_with("fake", app=firebase, check_revoked=True)
    resolve.assert_not_called()


def test_disabled_account_cannot_reach_identity(monkeypatch):
    verify = Mock(side_effect=security.auth.UserDisabledError("disabled"))
    resolve = Mock()
    monkeypatch.setattr(security, "firebase_app", object)
    monkeypatch.setattr(security.auth, "verify_id_token", verify)
    monkeypatch.setattr(security, "resolve_user", resolve)
    client = TestClient(app)
    assert client.get("/api/v1/incidencias", headers={"Authorization": "Bearer fake"}).status_code == 401
    resolve.assert_not_called()
