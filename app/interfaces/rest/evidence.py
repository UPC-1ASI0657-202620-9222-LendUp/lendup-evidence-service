from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.application.services.evidence import register_evidence
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


@router.post("/prestamos/{id}/evidencias", status_code=201)
def create_evidence(id: UUID, body: EvidenceRequest,
                    user: Principal = Depends(current_user),
                    session: Session = Depends(get_session)):
    return register_evidence(session, id, user, body.model_dump())
