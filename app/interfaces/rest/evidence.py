from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.application.services.evidence import list_evidence, register_evidence, upload_evidence
from app.domain.entities.evidence import EvidenceStage, EvidenceType
from app.infrastructure.persistence.database import get_session
from app.shared.security import Principal, current_user

router = APIRouter(prefix="/api/v1", tags=["Evidencias"])


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    etapa: EvidenceStage
    tipo: EvidenceType
    incidencia_id: UUID | None = None
    url: str | None = None
    cloudinary_public_id: str | None = Field(default=None, max_length=255)
    observacion: str | None = Field(default=None, max_length=10000)


@router.get("/prestamos/{id}/evidencias")
def get_evidence(id: UUID, user: Principal = Depends(current_user), session: Session = Depends(get_session)):
    return list_evidence(session, id, user)


@router.post("/prestamos/{id}/evidencias", status_code=201, openapi_extra={
    "requestBody": {"required": True, "content": {
        "application/json": {"schema": EvidenceRequest.model_json_schema()},
        "multipart/form-data": {"schema": {"type": "object", "required": ["etapa", "uploadId", "file"],
            "properties": {"etapa": {"type": "string", "enum": ["ENTREGA", "DEVOLUCION"]},
                           "uploadId": {"type": "string", "format": "uuid"},
                           "file": {"type": "string", "format": "binary"}}}}
    }}
})
async def create_evidence(id: UUID, request: Request,
                          user: Principal = Depends(current_user),
                          session: Session = Depends(get_session)):
    content_type = request.headers.get("content-type", "").split(";")[0].lower()
    if content_type == "application/json":
        try:
            body = EvidenceRequest.model_validate(await request.json())
        except (ValidationError, ValueError):
            raise HTTPException(400, "Evidencia inválida") from None
        return await run_in_threadpool(register_evidence, session, id, user, body.model_dump())
    if content_type == "multipart/form-data":
        async with request.form(max_files=1, max_fields=4) as form:
            file = form.get("file")
            try:
                stage = EvidenceStage(form.get("etapa"))
                upload_id = UUID(str(form.get("uploadId")))
            except (ValueError, TypeError):
                raise HTTPException(400, "etapa o uploadId inválido") from None
            if not isinstance(file, UploadFile):
                raise HTTPException(400, "Se requiere file")
            data = await file.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                raise HTTPException(413, "Máximo 5 MB")
            return await run_in_threadpool(upload_evidence, session, id, user, stage, upload_id, data, file.content_type or "")
    raise HTTPException(415, "Formato de solicitud no admitido")
