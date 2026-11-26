from uuid import UUID

import httpx
from fastapi import HTTPException

from app.shared.config import Settings
from app.shared.security import Principal


def participant_loan(loan_id: UUID, user: Principal) -> dict:
    base = Settings().loans_service_url
    if not base:
        raise HTTPException(503, "Préstamos no configurado")
    try:
        response = httpx.get(
            base.rstrip("/") + f"/api/v1/prestamos/{loan_id}",
            headers={"Authorization": f"Bearer {user.token}"}, timeout=5,
        )
        if response.status_code in (403, 404):
            raise HTTPException(response.status_code, "Préstamo no accesible")
        response.raise_for_status()
        loan = response.json()
        if str(loan["id"]) != str(loan_id):
            raise ValueError("Invalid loan response")
        if user.user_id not in (loan["prestamista_usuario_id"], loan["prestatario_usuario_id"]):
            raise HTTPException(403, "No participas en este préstamo")
        return loan
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo consultar Préstamos") from None


def administrative_loan(loan_id: UUID) -> dict:
    """Proposed private contract; fail closed until the Loans team implements it."""
    settings = Settings()
    if not settings.loans_service_url or len(settings.loans_service_token) < 32:
        raise HTTPException(503, "Contrato administrativo de Préstamos no configurado")
    try:
        response = httpx.get(
            settings.loans_service_url.rstrip("/") + f"/internal/v1/prestamos/{loan_id}/incidencias",
            headers={"Authorization": f"Bearer {settings.loans_service_token}"}, timeout=5,
        )
        response.raise_for_status()
        loan = response.json()
        if str(loan["id"]) != str(loan_id):
            raise ValueError("Invalid loan ID")
        from app.domain.entities.resolution import money
        loan["garantia_monetaria_acordada"] = money(loan["garantia_monetaria_acordada"])
        if not isinstance(loan["moneda"], str) or len(loan["moneda"]) != 3 or not loan["moneda"].isascii() or not loan["moneda"].isalpha() or not loan["moneda"].isupper():
            raise ValueError("Invalid currency")
        return loan
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo verificar la garantía en Préstamos") from None
