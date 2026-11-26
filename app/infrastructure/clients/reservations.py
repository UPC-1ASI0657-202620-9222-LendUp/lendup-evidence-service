from re import fullmatch
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.shared.config import Settings


def reservation_agreement(reservation_id: UUID) -> dict:
    settings = Settings()
    token = settings.reservations_service_token
    if (not settings.reservations_service_url or not fullmatch(r"[A-Za-z0-9_-]{32,}", token)
            or token in (settings.loans_service_token, settings.identity_service_token, settings.evidence_loans_service_token)):
        raise HTTPException(503, "Reservas no configurado para consultar el acuerdo")
    try:
        response = httpx.get(
            settings.reservations_service_url.rstrip("/") + f"/internal/v1/reservas/{reservation_id}/acuerdo",
            headers={"Authorization": f"Bearer {token}"}, timeout=3,
        )
        response.raise_for_status()
        agreement = response.json()
        if agreement["id"] != str(reservation_id):
            raise ValueError("Invalid reservation ID")
        return agreement
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo recuperar el acuerdo original de Reservas") from None
