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
