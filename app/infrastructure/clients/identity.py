from urllib.parse import quote
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.shared.config import Settings


def resolve_user(uid: str) -> str:
    settings = Settings()
    if not settings.identity_service_url or len(settings.identity_service_token) < 32:
        raise HTTPException(503, "Identidad no configurada")
    url = settings.identity_service_url.rstrip("/") + "/internal/v1/identidad/firebase/" + quote(uid, safe="")
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {settings.identity_service_token}"}, timeout=5)
        if response.status_code == 404:
            raise HTTPException(403, "Registra tu perfil en LendUp")
        response.raise_for_status()
        return str(UUID(response.json()["usuario_id"]))
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "No se pudo consultar Identidad") from None
