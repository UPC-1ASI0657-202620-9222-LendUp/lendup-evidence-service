from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.application.services.incident import detail, list_incidents, report, statement
from app.domain.entities.incident import IncidentType
from app.infrastructure.persistence.database import get_session
from app.shared.security import Principal, current_user

router = APIRouter(prefix="/api/v1", tags=["Incidencias"])


class IncidentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prestamo_id: UUID
    tipo: IncidentType
    descripcion: str = Field(min_length=20, max_length=10000)
    observaciones: list[str] = Field(default_factory=list, max_length=20)
    clave_idempotencia: UUID | None = None


class StatementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contenido: str = Field(min_length=20, max_length=10000)


@router.post("/incidencias", status_code=201, openapi_extra={
    "requestBody": {"required": True, "content": {
        "application/json": {"schema": {
            "type": "object", "required": ["prestamo_id", "tipo", "descripcion"],
            "properties": {"prestamo_id": {"type": "string", "format": "uuid"},
                           "tipo": {"type": "string", "enum": [item.value for item in IncidentType]},
                           "descripcion": {"type": "string", "minLength": 20, "maxLength": 10000},
                           "observaciones": {"type": "array", "maxItems": 20, "items": {"type": "string"}},
                           "clave_idempotencia": {"type": "string", "format": "uuid"}}}},
        "multipart/form-data": {"schema": {"type": "object", "required": ["reporte"],
            "properties": {"reporte": {"type": "string", "description": "JSON del reporte"},
                           "fotos": {"type": "array", "maxItems": 6, "items": {"type": "string", "format": "binary"}}}}}
    }}
})
async def create_incident(request: Request, user: Principal = Depends(current_user),
                          session: Session = Depends(get_session)):
    content_type = request.headers.get("content-type", "").split(";")[0].lower()
    photos = []
    try:
        if content_type == "application/json":
            body = IncidentRequest.model_validate(await request.json())
        elif content_type == "multipart/form-data":
            async with request.form(max_files=7, max_fields=2) as form:
                raw = form.get("reporte")
                if isinstance(raw, UploadFile):
                    raw = await raw.read(256 * 1024 + 1)
                if not isinstance(raw, (str, bytes)) or len(raw) > 256 * 1024:
                    raise HTTPException(400, "Reporte JSON inválido")
                body = IncidentRequest.model_validate_json(raw)
                for photo in form.getlist("fotos"):
                    if not isinstance(photo, UploadFile):
                        raise HTTPException(400, "Foto inválida")
                    data = await photo.read(5 * 1024 * 1024 + 1)
                    if len(data) > 5 * 1024 * 1024:
                        raise HTTPException(413, "Máximo 5 MB por foto")
                    photos.append(data)
        else:
            raise HTTPException(415, "Formato de solicitud no admitido")
    except (ValidationError, ValueError):
        raise HTTPException(400, "Reporte inválido") from None
    return await run_in_threadpool(report, session, user, body.model_dump(), photos)


@router.get("/incidencias")
def get_incidents(user: Principal = Depends(current_user), session: Session = Depends(get_session)):
    return list_incidents(session, user)


@router.get("/incidencias/{id}")
def get_incident_detail(id: UUID, user: Principal = Depends(current_user), session: Session = Depends(get_session)):
    return detail(session, id, user)


@router.post("/incidencias/{id}/descargo")
def create_statement(id: UUID, body: StatementRequest, user: Principal = Depends(current_user),
                     session: Session = Depends(get_session)):
    return statement(session, id, user, body.contenido)
