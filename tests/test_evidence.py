from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.domain.entities.evidence import EvidenceStage, EvidenceType, media_mime
from app.application.services.evidence import register_evidence
from app.shared.security import Principal

LOAN = UUID("11111111-1111-4111-8111-111111111111")
USER = Principal("firebase-uid", "user-1", "test-token")


def test_missing_token():
    with TestClient(app) as client:
        response = client.post(f"/api/v1/prestamos/{LOAN}/evidencias", json={"etapa": "ENTREGA", "tipo": "OBSERVACION"})
    assert response.status_code == 401


def test_media_signature():
    assert media_mime(b"\xff\xd8\xfftest") == "image/jpeg"
    with pytest.raises(ValueError):
        media_mime(b"invalid")


@patch("app.application.services.evidence.participant_loan")
def test_wrong_delivery_actor(loan):
    loan.return_value = {"prestamista_usuario_id": "other", "estado": "RESERVADO"}
    with pytest.raises(HTTPException) as error:
        register_evidence(Mock(), LOAN, USER, {"etapa": EvidenceStage.DELIVERY, "tipo": EvidenceType.NOTE})
    assert error.value.status_code == 403


@patch("app.application.services.evidence.evidence_registered")
@patch("app.application.services.evidence.enqueue")
@patch("app.application.services.evidence.EvidenceRepository")
@patch("app.application.services.evidence.participant_loan")
def test_register_note(loan, repository, enqueue, event):
    loan.return_value = {"prestamista_usuario_id": USER.user_id, "estado": "RESERVADO"}
    repository.return_value.add.side_effect = lambda values: values
    session = Mock()
    record = register_evidence(session, LOAN, USER, {"etapa": EvidenceStage.DELIVERY, "tipo": EvidenceType.NOTE, "observacion": "Objeto en buen estado"})
    assert record["estado_integracion"] == "COMPLETADA"
    assert record["registrada_por_usuario_id"] == USER.user_id
    enqueue.assert_called_once_with(session, event.return_value)
    session.commit.assert_called_once()
