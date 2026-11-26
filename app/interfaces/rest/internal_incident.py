from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.services.incident_closure import close_report_admission
from app.infrastructure.persistence.database import get_session
from app.shared.security import require_loans_service

router = APIRouter(prefix="/internal/v1/prestamos", include_in_schema=False)


@router.post("/{id}/cierre-incidencias", dependencies=[Depends(require_loans_service)])
def seal(id: UUID, session: Session = Depends(get_session)) -> list[str]:
    return close_report_admission(session, id)
