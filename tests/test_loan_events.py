import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.events.loan_events import IDS, validate_event, projection_changes
from app.infrastructure.messaging import loan_consumer


def created():
    p = {k: str(uuid4()) for k in IDS}
    p.update(garantia_requerida=True, garantia_monetaria_acordada=100, moneda="PEN",
             devolucion_original_en="2026-12-01T12:00:00")
    return dict(event_id=str(uuid4()), event_type="PrestamoCreado", event_version=1,
                aggregate_version=1, aggregate_id=p["prestamo_id"], occurred_at="2026-11-26T10:00:00Z",
                correlation_id="test", payload=p)


def test_creation_projection():
    e = validate_event("prestamos.creado.v1", created())
    row = {k: e["payload"][k] for k in IDS}
    row.update(aggregate_version=0, state_version=0, creation_version=0, date_version=0)
    result = projection_changes(row, e)
    assert result["estado"] == "RESERVADO"
    assert result["garantia_monetaria_acordada"] == 100


def test_late_creation_does_not_regress_state():
    e = validate_event("prestamos.creado.v1", created())
    row = {k: e["payload"][k] for k in IDS}
    row.update(aggregate_version=5, state_version=5, creation_version=0, date_version=5)
    result = projection_changes(row, e)
    assert "estado" not in result and "aggregate_version" not in result
    assert result["creation_version"] == 1


def test_route_mismatch():
    with pytest.raises(ValueError):
        validate_event("prestamos.activado.v1", created())


def test_missing_guarantee():
    e = created()
    del e["payload"]["garantia_monetaria_acordada"]
    with pytest.raises(ValueError):
        validate_event("prestamos.creado.v1", e)


def test_aggregate_mismatch():
    e = created()
    e["aggregate_id"] = str(uuid4())
    with pytest.raises(ValueError):
        validate_event("prestamos.creado.v1", e)


@pytest.mark.parametrize("processed", [True, False])
def test_ack_after_processing(monkeypatch, processed):
    monkeypatch.setattr(loan_consumer, "process_loan_event", lambda *args: processed)
    msg = AsyncMock()
    msg.body = b'{}'
    msg.routing_key = "prestamos.creado.v1"
    asyncio.run(loan_consumer.handle_message(msg))
    msg.ack.assert_awaited_once()
    msg.reject.assert_not_awaited()


def test_invalid_message_rejected():
    msg = AsyncMock()
    msg.body = b'not json'
    asyncio.run(loan_consumer.handle_message(msg))
    msg.reject.assert_awaited_once_with(requeue=False)
    msg.ack.assert_not_awaited()
