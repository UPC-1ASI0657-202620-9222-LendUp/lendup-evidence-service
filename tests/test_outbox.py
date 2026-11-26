from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

import pytest

from app.domain.events.events import evidence_registered, incident_event, ROUTES
from app.infrastructure.messaging import relay
from app.infrastructure.messaging.outbox import enqueue, retry_delay


def sample():
    incident = dict(id=str(uuid4()), prestamo_id=str(uuid4()), tipo="DANIO",
                    reportada_por_usuario_id=str(uuid4()), decision_garantia="AFECTACION_PARCIAL",
                    monto_garantia_afectado=Decimal("10.50"), moneda="PEN",
                    justificacion_resolucion="Justificación de prueba")
    loan = dict(prestatario_usuario_id=str(uuid4()), prestamista_usuario_id=str(uuid4()))
    return incident, loan


def test_incident_reported_contract():
    incident, loan = sample()
    event = incident_event(incident, loan)
    assert event["event_type"] == "IncidenciaReportada"
    assert event["event_version"] == 1
    assert event["aggregate_version"] == 1
    assert event["aggregate_id"] == incident["id"]
    assert event["payload"]["prestamo_id"] == incident["prestamo_id"]
    assert event["payload"]["prestamista_usuario_id"] == loan["prestamista_usuario_id"]
    assert ROUTES[event["event_type"]] == "evidencias.incidencia-reportada.v1"


def test_incident_resolved_contract():
    incident, loan = sample()
    event = incident_event(incident, loan, resolved=True)
    assert event["event_type"] == "IncidenciaResuelta"
    assert event["aggregate_version"] == 2
    assert event["payload"]["monto_garantia_afectado"] == 10.50
    assert event["payload"]["decision_garantia"] == "AFECTACION_PARCIAL"
    assert event["payload"]["moneda"] == "PEN"
    assert ROUTES[event["event_type"]] == "evidencias.incidencia-resuelta.v1"


def test_evidence_event_omits_sensitive_content():
    record = dict(id=str(uuid4()), prestamo_id=str(uuid4()), registrada_por_usuario_id=str(uuid4()),
                  etapa="ENTREGA", tipo="FOTO", url="private", observacion="private")
    event = evidence_registered(record)
    assert event["event_type"] == "EvidenciaRegistrada"
    assert "url" not in event["payload"] and "observacion" not in event["payload"]


def test_enqueue_does_not_commit():
    session = Mock()
    incident, loan = sample()
    enqueue(session, incident_event(incident, loan))
    session.execute.assert_called_once()
    session.commit.assert_not_called()
    statement = session.execute.call_args.args[0]
    assert statement.table.name == "outbox_events"
    assert statement.compile().params["mandatory"] is True


def test_retry_is_bounded():
    assert retry_delay(1) == 2
    assert retry_delay(4) == 16
    assert retry_delay(100) == 300


def mock_relay(monkeypatch):
    session = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=session)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(relay, "Session", lambda _: context)
    engine = Mock()
    connection = engine.connect.return_value.execution_options.return_value
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(relay, "get_engine", lambda: engine)
    row = dict(id=str(uuid4()), attempts=0)
    monkeypatch.setattr(relay, "next_event", lambda _: row)
    return session, row


def test_relay_confirm_marks_published(monkeypatch):
    session, row = mock_relay(monkeypatch)
    monkeypatch.setattr(relay, "publish_event", AsyncMock())
    success, failure = Mock(), Mock()
    monkeypatch.setattr(relay, "mark_published", success)
    monkeypatch.setattr(relay, "mark_failure", failure)
    assert relay.relay_once(Mock())
    success.assert_called_once_with(session, row)
    failure.assert_not_called()
    session.commit.assert_called_once()


def test_relay_failure_keeps_event(monkeypatch):
    session, row = mock_relay(monkeypatch)
    error = TimeoutError()
    monkeypatch.setattr(relay, "publish_event", AsyncMock(side_effect=error))
    success, failure = Mock(), Mock()
    monkeypatch.setattr(relay, "mark_published", success)
    monkeypatch.setattr(relay, "mark_failure", failure)
    assert relay.relay_once(Mock())
    failure.assert_called_once_with(session, row, error)
    success.assert_not_called()
    session.commit.assert_called_once()


def test_relay_empty(monkeypatch):
    session, _ = mock_relay(monkeypatch)
    monkeypatch.setattr(relay, "next_event", lambda _: None)
    publish = AsyncMock()
    monkeypatch.setattr(relay, "publish_event", publish)
    assert relay.relay_once(Mock()) is False
    publish.assert_not_awaited()
    session.rollback.assert_called_once()
