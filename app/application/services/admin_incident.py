from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.application.services.incident import ordered, get_incident, validate_content
from app.domain.entities.incident import GuaranteeDecision
from app.domain.events.events import incident_event
from app.infrastructure.messaging.outbox import enqueue
from app.domain.entities.resolution import money, remaining_guarantee, validate_decision
from app.infrastructure.clients.loans import administrative_loan
from app.infrastructure.persistence.models import incidents
from app.infrastructure.persistence.repositories import EvidenceRepository, IncidentNoteRepository
from app.shared.security import Principal


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_detail(session: Session, incident: dict) -> dict:
    repo = EvidenceRepository(session)
    rows = ordered(repo.list_by(incidencia_id=incident["id"]))
    result = dict(incident, evidencias=rows,
                  observaciones=ordered(IncidentNoteRepository(session).list_by(incidencia_id=incident["id"])),
                  evidencias_prestamo=ordered(repo.list_by(prestamo_id=incident["prestamo_id"])))
    for row in rows:
        if row["tipo"] == "OBSERVACION" and row["registrada_por_usuario_id"] != incident["reportada_por_usuario_id"]:
            result.update(descargo=row["observacion"], descargo_en=row["registrada_en"])
            break
    return result


def admin_list(session: Session, state: str | None, kind: str | None) -> list[dict]:
    stmt = select(incidents)
    if state is not None:
        stmt = stmt.where(incidents.c.estado == state)
    if kind is not None:
        stmt = stmt.where(incidents.c.tipo == kind)
    rows = session.execute(stmt.order_by(incidents.c.reportada_en.desc(), incidents.c.id)).mappings().all()
    return [local_detail(session, dict(row)) for row in rows]


def locked_incident(session: Session, incident_id: UUID) -> dict:
    row = session.execute(select(incidents).where(incidents.c.id == str(incident_id)).with_for_update()).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Incidencia no encontrada")
    return dict(row)


def require_open(incident: dict):
    if incident["estado"] == "RESUELTA":
        raise HTTPException(409, "La incidencia ya está resuelta")


def require_review(incident: dict):
    require_open(incident)
    if incident["estado"] != "EN_REVISION":
        raise HTTPException(409, "Inicia la revisión primero")


def change(session: Session, incident: dict, values: dict) -> dict:
    session.execute(update(incidents).where(incidents.c.id == incident["id"]).values(**values))
    return dict(incident, **values)


def review(session: Session, incident_id: UUID) -> dict:
    incident = locked_incident(session, incident_id)
    require_open(incident)
    if incident["estado"] != "EN_REVISION":
        timestamp = now()
        incident = change(session, incident, dict(estado="EN_REVISION", revision_iniciada_en=timestamp, actualizada_en=timestamp))
    session.commit()
    return local_detail(session, incident)


def add_observation(session: Session, incident_id: UUID, admin: Principal, content: str) -> dict:
    content = validate_content(content, 1)
    incident = locked_incident(session, incident_id)
    require_review(incident)
    IncidentNoteRepository(session).add(dict(incidencia_id=incident["id"],
                                            administrador_usuario_id=admin.user_id, contenido=content))
    session.commit()
    return local_detail(session, incident)


def resolve(session: Session, incident_id: UUID, admin: Principal, justification: str,
            decision: GuaranteeDecision, amount: Decimal) -> dict:
    justification = validate_content(justification, 20)
    try:
        amount = money(amount)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    initial = get_incident(session, incident_id)
    require_review(initial)
    loan = administrative_loan(UUID(initial["prestamo_id"]))
    # Serialize resolutions across ALL incidents of the same loan, in stable order.
    # Locking reads observe the latest committed decisions under MySQL REPEATABLE READ.
    rows = session.execute(select(incidents).where(incidents.c.prestamo_id == initial["prestamo_id"])
                           .order_by(incidents.c.id).with_for_update()).mappings().all()
    incident = next((dict(row) for row in rows if row["id"] == str(incident_id)), None)
    if incident is None:
        raise HTTPException(404, "Incidencia no encontrada")
    require_review(incident)
    try:
        previous = sum((money(row["monto_garantia_afectado"]) for row in rows if row["estado"] == "RESUELTA"), Decimal("0.00"))
        available = remaining_guarantee(loan["garantia_monetaria_acordada"], previous)
        amount = validate_decision(decision, amount, available)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    timestamp = now()
    incident = change(session, incident, dict(
        estado="RESUELTA", resuelta_en=timestamp, resuelta_por_usuario_id=admin.user_id,
        justificacion_resolucion=justification, decision_garantia=decision.value,
        monto_garantia_afectado=amount, saldo_garantia_previsto=available - amount,
        moneda=loan["moneda"], actualizada_en=timestamp))
    enqueue(session, incident_event(incident, loan, resolved=True))
    session.commit()
    # This records a decision only; it does not charge, capture or refund money.
    return local_detail(session, incident)
