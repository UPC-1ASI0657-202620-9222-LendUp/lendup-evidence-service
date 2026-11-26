from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.entities.evidence import EvidenceStage, EvidenceType
from app.infrastructure.clients.loans import participant_loan
from app.infrastructure.persistence.repositories import EvidenceRepository, IncidentRepository
from app.shared.security import Principal


def register_evidence(session: Session, loan_id: UUID, user: Principal, data: dict) -> dict:
    loan = participant_loan(loan_id, user)
    stage = data["etapa"]
    kind = data["tipo"]
    if stage == EvidenceStage.DELIVERY and (loan["prestamista_usuario_id"] != user.user_id or loan["estado"] != "RESERVADO"):
        raise HTTPException(403 if loan["prestamista_usuario_id"] != user.user_id else 409, "Entrega no permitida")
    if stage == EvidenceStage.RETURN and (loan["prestatario_usuario_id"] != user.user_id or loan["estado"] not in ("ACTIVO", "VENCIDO")):
        raise HTTPException(403 if loan["prestatario_usuario_id"] != user.user_id else 409, "Devolución no permitida")
    incident_id = data.get("incidencia_id")
    if incident_id or stage == EvidenceStage.INCIDENT:
        incident = IncidentRepository(session).get(str(incident_id)) if incident_id else None
        if not incident or incident["prestamo_id"] != str(loan_id) or stage != EvidenceStage.INCIDENT:
            raise HTTPException(400, "Incidencia incompatible")
        if incident["estado"] == "RESUELTA":
            raise HTTPException(409, "Incidencia resuelta")
    values = {"prestamo_id": str(loan_id), "registrada_por_usuario_id": user.user_id,
              "etapa": stage.value, "tipo": kind.value}
    if incident_id:
        values["incidencia_id"] = str(incident_id)
    if kind == EvidenceType.NOTE:
        if not (data.get("observacion") or "").strip():
            raise HTTPException(400, "Falta observacion")
        values.update(observacion=data["observacion"], estado_integracion="COMPLETADA")
    else:
        # Do not trust arbitrary external URLs or asset IDs as proof of ownership.
        if data.get("url") or data.get("cloudinary_public_id"):
            raise HTTPException(400, "Usa la subida multipart para registrar archivos verificados")
        values["estado_integracion"] = "PENDIENTE"
    record = EvidenceRepository(session).add(values)
    session.commit()
    return record
