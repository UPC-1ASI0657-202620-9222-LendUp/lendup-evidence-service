import asyncio

import pytest

from app.infrastructure.gemini.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from app.infrastructure.gemini.adapter import counts_provider_failure
from app.application.services import analysis
from unittest.mock import AsyncMock, Mock
from uuid import uuid4


class Clock:
    value = 0.0

    def __call__(self):
        return self.value


async def fail():
    raise TimeoutError()


async def succeed():
    return "ok"


def open_circuit(breaker):
    for _ in range(3):
        with pytest.raises(TimeoutError):
            asyncio.run(breaker.call(fail))


def test_opens_after_three_failures():
    breaker = CircuitBreaker(clock=Clock())
    for _ in range(2):
        with pytest.raises(TimeoutError):
            asyncio.run(breaker.call(fail))
        assert breaker.state == CircuitState.CLOSED
    with pytest.raises(TimeoutError):
        asyncio.run(breaker.call(fail))
    assert breaker.state == CircuitState.OPEN
    operation = AsyncMock()
    with pytest.raises(CircuitOpenError):
        asyncio.run(breaker.call(operation))
    operation.assert_not_awaited()


def test_success_resets_failures():
    breaker = CircuitBreaker(clock=Clock())
    for _ in range(2):
        with pytest.raises(TimeoutError):
            asyncio.run(breaker.call(fail))
    assert asyncio.run(breaker.call(succeed)) == "ok"
    for _ in range(2):
        with pytest.raises(TimeoutError):
            asyncio.run(breaker.call(fail))
    assert breaker.state == CircuitState.CLOSED


def test_single_probe_and_recovery():
    clock = Clock()
    breaker = CircuitBreaker(clock=clock)
    open_circuit(breaker)
    clock.value = 59
    with pytest.raises(CircuitOpenError):
        breaker.acquire()
    clock.value = 60
    permit = breaker.acquire()
    assert breaker.state == CircuitState.HALF_OPEN
    with pytest.raises(CircuitOpenError):
        breaker.acquire()
    breaker.success(permit)
    assert breaker.state == CircuitState.CLOSED


def test_failed_probe_reopens():
    clock = Clock()
    breaker = CircuitBreaker(clock=clock)
    open_circuit(breaker)
    clock.value = 60
    with pytest.raises(TimeoutError):
        asyncio.run(breaker.call(fail))
    assert breaker.state == CircuitState.OPEN
    clock.value = 119
    with pytest.raises(CircuitOpenError):
        breaker.acquire()


def test_stale_success_does_not_close_open_circuit():
    breaker = CircuitBreaker(clock=Clock())
    old = breaker.acquire()
    open_circuit(breaker)
    breaker.success(old)
    assert breaker.state == CircuitState.OPEN


def test_cancelled_probe_reopens():
    clock = Clock()
    breaker = CircuitBreaker(clock=clock)
    open_circuit(breaker)
    clock.value = 60

    async def cancelled():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(breaker.call(cancelled))
    assert breaker.state == CircuitState.OPEN


def test_invalid_input_does_not_open_circuit():
    breaker = CircuitBreaker(clock=Clock())

    async def invalid():
        raise ValueError("invalid photo")

    for _ in range(4):
        with pytest.raises(ValueError):
            asyncio.run(breaker.call(invalid, counts_provider_failure))
    assert breaker.state == CircuitState.CLOSED


def test_open_circuit_persists_fallback(monkeypatch):
    loan = str(uuid4())
    common = dict(prestamo_id=loan, tipo="FOTO", estado_integracion="COMPLETADA",
                  url="https://res.cloudinary.com/test/image/upload/photo.jpg", cloudinary_public_id="photo")
    monkeypatch.setattr(analysis, "claim_analysis", lambda _: (
        {"prestamo_id": loan}, dict(common, etapa="ENTREGA"), dict(common, etapa="DEVOLUCION")))
    adapter = Mock(compare=AsyncMock(side_effect=CircuitOpenError()))
    monkeypatch.setattr(analysis, "GoogleAIAdapter", lambda: adapter)
    finish = Mock()
    monkeypatch.setattr(analysis, "finish_analysis", finish)
    asyncio.run(analysis.process_analysis("test"))
    values = finish.call_args.args[1]
    assert values["estado"] == "FALLIDO"
    assert "temporalmente" in values["error_descripcion"]
