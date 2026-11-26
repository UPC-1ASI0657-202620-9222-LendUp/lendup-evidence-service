import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.application.services import analysis
from app.domain.entities.analysis import AnalysisResult
from app.infrastructure.gemini.adapter import verified_image_url
from app.main import app


def pair():
    loan = uuid4()
    common = dict(prestamo_id=str(loan), tipo="FOTO", estado_integracion="COMPLETADA",
                  url="https://res.cloudinary.com/test/image/upload/photo.jpg", cloudinary_public_id="photo")
    return loan, dict(common, etapa="ENTREGA"), dict(common, etapa="DEVOLUCION")


def test_valid_pair():
    loan, first, last = pair()
    analysis.validate_pair(first, last, loan)


def test_invalid_pair():
    loan, first, last = pair()
    for invalid in [None, dict(last, tipo="VIDEO"), dict(last, etapa="ENTREGA"),
                    dict(last, prestamo_id=str(uuid4())), dict(last, estado_integracion="PENDIENTE")]:
        with pytest.raises(HTTPException) as error:
            analysis.validate_pair(first, invalid, loan)
        assert error.value.status_code == 400


def test_cloudinary_url_allowlist():
    url = "https://res.cloudinary.com/test/image/upload/photo.jpg"
    assert verified_image_url(url, "test") == url
    for invalid in ["http://res.cloudinary.com/test/image/upload/a", "https://evil.example/a",
                    "https://res.cloudinary.com/other/image/upload/a",
                    "https://res.cloudinary.com/test/image/upload/a?x=1"]:
        with pytest.raises(ValueError):
            verified_image_url(invalid, "test")


def test_analysis_authentication():
    client = TestClient(app)
    loan, first, last = str(uuid4()), str(uuid4()), str(uuid4())
    base = f"/api/v1/prestamos/{loan}/analisis-evidencias"
    assert client.post(base, json={"evidencia_inicial_id": first, "evidencia_final_id": last}).status_code == 401
    assert client.get(f"{base}/{first}").status_code == 401


def test_analysis_success(monkeypatch):
    loan, first, last = pair()
    monkeypatch.setattr(analysis, "claim_analysis", lambda _: ({"prestamo_id": str(loan)}, first, last))
    result = AnalysisResult(resumen="Sin cambios visibles", diferencias_visibles=[], limitaciones=[], comparabilidad="MEDIA")
    adapter = Mock(compare=AsyncMock(return_value=result))
    monkeypatch.setattr(analysis, "GoogleAIAdapter", lambda: adapter)
    finish = Mock()
    monkeypatch.setattr(analysis, "finish_analysis", finish)
    asyncio.run(analysis.process_analysis("test"))
    values = finish.call_args.args[1]
    assert values["estado"] == "COMPLETADO"
    assert values["resultado_detalle"]["requiere_revision_humana"] is True


def test_analysis_failure(monkeypatch):
    loan, first, last = pair()
    monkeypatch.setattr(analysis, "claim_analysis", lambda _: ({"prestamo_id": str(loan)}, first, last))
    adapter = Mock(compare=AsyncMock(side_effect=TimeoutError()))
    monkeypatch.setattr(analysis, "GoogleAIAdapter", lambda: adapter)
    finish = Mock()
    monkeypatch.setattr(analysis, "finish_analysis", finish)
    asyncio.run(analysis.process_analysis("test"))
    assert finish.call_args.args[1]["estado"] == "FALLIDO"


def test_already_claimed(monkeypatch):
    monkeypatch.setattr(analysis, "claim_analysis", lambda _: None)
    finish = Mock()
    monkeypatch.setattr(analysis, "finish_analysis", finish)
    asyncio.run(analysis.process_analysis("test"))
    finish.assert_not_called()
