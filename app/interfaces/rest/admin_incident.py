from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.application.services.admin_incident import admin_list, review, add_observation, resolve
from app.domain.entities.incident import IncidentState, IncidentType, GuaranteeDecision
from app.infrastructure.persistence.database import get_session
from app.shared.security import Principal, current_admin

router = APIRouter(prefix="/api/v1/admin/incidencias", tags=["Administración de Incidencias"])


class ObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contenido: str = Field(min_length=1, max_length=10000)


class ResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    justificacion_resolucion: str = Field(min_length=20, max_length=10000)
    decision_garantia: GuaranteeDecision
    monto_garantia_afectado: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)


@router.get("")
def list_admin_incidents(estado: IncidentState | None = None, tipo: IncidentType | None = None,
                         admin: Principal = Depends(current_admin), session: Session = Depends(get_session)):
    return admin_list(session, estado.value if estado else None, tipo.value if tipo else None)


@router.post("/{id}/revision")
def review_incident(id: UUID, admin: Principal = Depends(current_admin), session: Session = Depends(get_session)):
    return review(session, id)


@router.post("/{id}/observaciones")
def observe_incident(id: UUID, body: ObservationRequest, admin: Principal = Depends(current_admin),
                     session: Session = Depends(get_session)):
    return add_observation(session, id, admin, body.contenido)


@router.post("/{id}/resolucion")
def resolve_incident(id: UUID, body: ResolutionRequest, admin: Principal = Depends(current_admin),
                     session: Session = Depends(get_session)):
    return resolve(session, id, admin, body.justificacion_resolucion,
                   body.decision_garantia, body.monto_garantia_afectado)
