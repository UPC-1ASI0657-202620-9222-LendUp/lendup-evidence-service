from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.application.services.analysis import request_analysis, read_analysis, process_analysis
from app.infrastructure.persistence.database import get_session
from app.shared.security import Principal, current_user

router = APIRouter(prefix="/api/v1", tags=["Análisis de Evidencias"])


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidencia_inicial_id: UUID
    evidencia_final_id: UUID
    incidencia_id: UUID | None = None


@router.post("/prestamos/{id}/analisis-evidencias", status_code=201)
def create_analysis(id: UUID, body: AnalysisRequest, tasks: BackgroundTasks,
                    user: Principal = Depends(current_user), session: Session = Depends(get_session)):
    row = request_analysis(session, id, user, body.model_dump())
    tasks.add_task(process_analysis, row["id"])
    return row


@router.get("/prestamos/{id}/analisis-evidencias/{analisis_id}")
def get_analysis(id: UUID, analisis_id: UUID, user: Principal = Depends(current_user),
                 session: Session = Depends(get_session)):
    return read_analysis(session, id, analisis_id, user)
