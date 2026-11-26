from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities.evidence import media_mime
from app.domain.entities.incident import clean_content
from app.infrastructure.clients.loans import participant_loan
from app.infrastructure.cloudinary.storage import CloudinaryStorage
from app.infrastructure.persistence.models import incidents
from app.infrastructure.persistence.repositories import (
    EvidenceRepository, IncidentNoteRepository, IncidentRepository,
)
from app.shared.security import Principal


def ordered(rows):
    return sorted(rows, key=lambda row: (row["registrada_en"], row["id"]))


def decorate(session: Session, incident: dict, loan: dict) -> dict:
    repo = EvidenceRepository(session)
    rows = ordered(repo.list_by(incidencia_id=incident["id"]))
    result = dict(incident)
    result["prestamo"] = dict(loan, evidencias=ordered(repo.list_by(prestamo_id=incident["prestamo_id"])))
    result["garantia_monetaria_acordada"] = loan.get("garantia_monetaria_acordada")
    result["evidencias"] = rows
    result["observaciones"] = ordered(IncidentNoteRepository(session).list_by(incidencia_id=incident["id"]))
    for row in rows:
        if row["tipo"] == "OBSERVACION" and row["registrada_por_usuario_id"] != incident["reportada_por_usuario_id"]:
            result.update(descargo=row["observacion"], descargo_en=row["registrada_en"])
            break
    return result


def get_incident(session: Session, incident_id: UUID) -> dict:
    row = IncidentRepository(session).get(str(incident_id))
    if row is None:
        raise HTTPException(404, "Incidencia no encontrada")
    return row


def detail(session: Session, incident_id: UUID, user: Principal) -> dict:
    incident = get_incident(session, incident_id)
    loan = participant_loan(UUID(incident["prestamo_id"]), user)
    return decorate(session, incident, loan)


def list_incidents(session: Session, user: Principal) -> list[dict]:
    # Until Loans exposes a participant loan-list contract, authorize each distinct loan.
    rows = session.execute(select(incidents).order_by(incidents.c.reportada_en.desc(), incidents.c.id)).mappings()
    candidates = [dict(row) for row in rows]
    loans = {}
    results = []
    for incident in candidates:
        loan_id = incident["prestamo_id"]
        if loan_id not in loans:
            try:
                loans[loan_id] = participant_loan(UUID(loan_id), user)
            except HTTPException as exc:
                if exc.status_code not in (403, 404):
                    raise
                loans[loan_id] = None
        if loans[loan_id] is not None:
            results.append(decorate(session, incident, loans[loan_id]))
    return results


def validate_content(value: str, minimum: int) -> str:
    try:
        return clean_content(value, minimum)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


def note_values(incident: dict, user: Principal, content: str) -> dict:
    return dict(prestamo_id=incident["prestamo_id"], incidencia_id=incident["id"],
                registrada_por_usuario_id=user.user_id, etapa="INCIDENCIA",
                tipo="OBSERVACION", observacion=content, estado_integracion="COMPLETADA")


def report(session: Session, user: Principal, body: dict, photos: list[bytes]) -> dict:
    loan_id = body["prestamo_id"]
    loan = participant_loan(loan_id, user)
    description = validate_content(body["descripcion"], 20)
    notes = [validate_content(note, 1) for note in body.get("observaciones", [])]
    if len(notes) > 20 or len(photos) > 6:
        raise HTTPException(400, "Máximo 6 fotos y 20 observaciones")
    validated = []
    for data in photos:
        try:
            mime = media_mime(data)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        if not mime.startswith("image/"):
            raise HTTPException(400, "Solo se admiten fotografías")
        validated.append((data, mime))
    incident_id = str(body.get("clave_idempotencia") or uuid4())
    values = dict(id=incident_id, prestamo_id=str(loan_id), reportada_por_usuario_id=user.user_id,
                  tipo=body["tipo"].value, descripcion=description, estado="PENDIENTE")
    repo = IncidentRepository(session)

    def replay(existing):
        if any(existing[key] != values[key] for key in ("prestamo_id", "reportada_por_usuario_id", "tipo", "descripcion")):
            raise HTTPException(409, "La clave ya corresponde a otro reporte")
        return decorate(session, existing, loan)

    existing = repo.get(incident_id)
    if existing:
        return replay(existing)
    if loan["estado"] in ("FINALIZADO", "CANCELADO"):
        raise HTTPException(409, "El préstamo está cerrado")
    storage = CloudinaryStorage() if validated else None
    uploaded = []
    try:
        try:
            incident = repo.add(values)
        except IntegrityError:
            session.rollback()
            existing = repo.get(incident_id)
            if existing:
                return replay(existing)
            raise
        evidence_repo = EvidenceRepository(session)
        for note in notes:
            evidence_repo.add(note_values(incident, user, note))
        for data, mime in validated:
            asset = storage.upload(data, mime, f"lendup/incidencias/{incident_id}/{uuid4()}", "lendup/incidencias")
            uploaded.append(asset.public_id)
            evidence_repo.add(dict(prestamo_id=str(loan_id), incidencia_id=incident_id,
                                   registrada_por_usuario_id=user.user_id, etapa="INCIDENCIA",
                                   tipo="FOTO", url=asset.url, cloudinary_public_id=asset.public_id,
                                   estado_integracion="COMPLETADA"))
        result = decorate(session, incident, loan)
    except Exception:
        session.rollback()
        for public_id in uploaded:
            storage.delete(public_id, False)
        raise
    # A failed commit may be ambiguous; preserve uploaded assets for reconciliation.
    session.commit()
    return result


def statement(session: Session, incident_id: UUID, user: Principal, content: str) -> dict:
    incident = get_incident(session, incident_id)
    loan = participant_loan(UUID(incident["prestamo_id"]), user)
    content = validate_content(content, 20)
    # Serialize competing statements and future admin state changes on the same row.
    locked = session.execute(select(incidents).where(incidents.c.id == str(incident_id)).with_for_update()).mappings().one()
    incident = dict(locked)
    if incident["estado"] == "RESUELTA":
        raise HTTPException(409, "La incidencia ya está resuelta")
    if incident["reportada_por_usuario_id"] == user.user_id:
        raise HTTPException(403, "Solo la contraparte puede presentar el descargo")
    # Locking read avoids stale snapshots under MySQL REPEATABLE READ.
    from app.infrastructure.persistence.models import evidence
    previous = session.execute(select(evidence.c.id).where(
        evidence.c.incidencia_id == str(incident_id),
        evidence.c.registrada_por_usuario_id == user.user_id,
        evidence.c.tipo == "OBSERVACION",
    ).with_for_update()).first()
    if previous:
        raise HTTPException(409, "Ya presentaste tu descargo")
    EvidenceRepository(session).add(note_values(incident, user, content))
    session.commit()
    return decorate(session, incident, loan)
