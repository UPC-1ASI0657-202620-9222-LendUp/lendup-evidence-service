from dataclasses import dataclass
from hmac import compare_digest
from re import fullmatch
from threading import Lock

import firebase_admin
from firebase_admin import auth
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.clients.identity import resolve_user, resolve_role
from app.shared.config import Settings

bearer = HTTPBearer(auto_error=False)
_lock = Lock()


@dataclass(frozen=True)
class Principal:
    uid: str
    user_id: str
    token: str


def firebase_app():
    project = Settings().firebase_project_id
    if not project:
        raise HTTPException(503, "Firebase no configurado")
    with _lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            try:
                return firebase_admin.initialize_app(options={"projectId": project})
            except Exception:
                raise HTTPException(503, "Firebase no disponible") from None


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Autenticación requerida", headers={"WWW-Authenticate": "Bearer"})
    app = firebase_app()
    try:
        claims = auth.verify_id_token(credentials.credentials, app=app, check_revoked=True)
        uid = claims["uid"]
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError,
            auth.UserNotFoundError, ValueError, KeyError):
        raise HTTPException(401, "Token inválido", headers={"WWW-Authenticate": "Bearer"}) from None
    except Exception:
        raise HTTPException(503, "Firebase no disponible") from None
    if claims.get("email_verified") is not True:
        raise HTTPException(403, "Verifica tu correo antes de continuar")
    return Principal(uid, resolve_user(uid), credentials.credentials)


def current_admin(user: Principal = Depends(current_user)) -> Principal:
    if resolve_role(user.user_id) != "ADMINISTRADOR":
        raise HTTPException(403, "Se requiere rol ADMINISTRADOR")
    return user


def require_loans_service(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    settings = Settings()
    expected = settings.evidence_loans_service_token
    if (not credentials or not fullmatch(r"[A-Za-z0-9_-]{32,}", expected)
            or expected in (settings.loans_service_token, settings.identity_service_token, settings.reservations_service_token)
            or not compare_digest(expected.encode(), credentials.credentials.encode())):
        raise HTTPException(401, "Credencial de servicio inválida")
