from uuid import UUID

import httpx
from fastapi import HTTPException

from app.shared.config import Settings
from app.shared.security import Principal


def participant_loan(loan_id: UUID, user: Principal) -> dict:
    return loan_view(loan_id, user.user_id)


def loan_view(loan_id: UUID, participant_id: str) -> dict:
    settings = Settings()
    if not settings.loans_service_url or len(settings.loans_service_token) < 32:
        raise HTTPException(503, "Préstamos no configurado")
    try:
        response = httpx.get(
            settings.loans_service_url.rstrip("/") + f"/internal/v1/prestamos/{loan_id}/participantes/{UUID(participant_id)}",
            headers={"Authorization": f"Bearer {settings.loans_service_token}"}, timeout=5,
        )
        if response.status_code in (403, 404):
            raise HTTPException(response.status_code, "Préstamo no accesible")
        response.raise_for_status()
        loan = response.json()
        if str(loan["id"]) != str(loan_id):
            raise ValueError("Invalid loan response")
        if participant_id not in (loan["prestamista_usuario_id"], loan["prestatario_usuario_id"]):
            raise HTTPException(403, "No participas en este préstamo")
        return loan
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo consultar Préstamos") from None


def administrative_loan(loan_id: UUID) -> dict:
    settings = Settings()
    if not settings.loans_service_url or len(settings.loans_service_token) < 32:
        raise HTTPException(503, "Contrato administrativo de Préstamos no configurado")
    try:
        response = httpx.get(
            settings.loans_service_url.rstrip("/") + f"/internal/v1/prestamos/{loan_id}/incidencias",
            headers={"Authorization": f"Bearer {settings.loans_service_token}"}, timeout=5,
        )
        if response.status_code == 404:
            raise HTTPException(404, "Préstamo no encontrado")
        response.raise_for_status()
        loan = response.json()
        if str(loan["id"]) != str(loan_id):
            raise ValueError("Invalid loan ID")
        from app.domain.entities.resolution import money
        amount = loan["garantia_monetaria_acordada"]
        loan["garantia_monetaria_acordada"] = money(amount) if amount is not None else None
        for field in ("prestamista_usuario_id", "prestatario_usuario_id"):
            loan[field] = str(UUID(str(loan[field])))
        if not isinstance(loan["moneda"], str) or len(loan["moneda"]) != 3 or not loan["moneda"].isascii() or not loan["moneda"].isalpha() or not loan["moneda"].isupper():
            raise ValueError("Invalid currency")
        return loan
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo verificar la garantía en Préstamos") from None


def loan_accepts_reports(loan_id: UUID) -> bool:
    settings = Settings()
    if not settings.loans_service_url or len(settings.loans_service_token) < 32:
        raise HTTPException(503, "Préstamos no configurado")
    try:
        response = httpx.get(
            settings.loans_service_url.rstrip("/") + f"/internal/v1/prestamos/{loan_id}/admision-incidencias",
            headers={"Authorization": f"Bearer {settings.loans_service_token}"}, timeout=5,
        )
        response.raise_for_status()
        accepts = response.json()["admite_reportes"]
        if type(accepts) is not bool:
            raise ValueError("Invalid report admission response")
        return accepts
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo verificar el estado del cierre en Préstamos") from None
