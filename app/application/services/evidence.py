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
        if kind == EvidenceType.NOTE and incident["reportada_por_usuario_id"] != user.user_id:
            raise HTTPException(403, "Usa el endpoint de descargo para registrar una observación de la contraparte")
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


def upload_evidence(session: Session, loan_id: UUID, user: Principal, stage: EvidenceStage,
                    upload_id: UUID, data: bytes, declared_mime: str) -> dict:
    from sqlalchemy import text
    from app.domain.entities.evidence import media_mime
    from app.infrastructure.cloudinary.storage import CloudinaryStorage

    if stage not in (EvidenceStage.DELIVERY, EvidenceStage.RETURN):
        raise HTTPException(400, "Usa ENTREGA o DEVOLUCION")
    loan = participant_loan(loan_id, user)
    actor = "prestamista_usuario_id" if stage == EvidenceStage.DELIVERY else "prestatario_usuario_id"
    if loan[actor] != user.user_id:
        raise HTTPException(403, "Operación no permitida")
    try:
        mime = media_mime(data, declared_mime)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    video = mime.startswith("video/")
    folder = f"lendup/evidencias/{'entrega' if stage == EvidenceStage.DELIVERY else 'devolucion'}"
    public_id = f"lendup/evidencias/{loan_id}/{stage.value.lower()}/{upload_id}"
    # MySQL advisory lock is connection-scoped: pin a connection until release.
    lock_name = f"ev:{loan_id}:{stage.value}"
    with session.get_bind().connect() as connection:
        locked = connection.execute(text("SELECT GET_LOCK(:name, 10)"), {"name": lock_name}).scalar()
        if locked != 1:
            raise HTTPException(503, "Registro ocupado; reintenta")
        try:
            with Session(bind=connection) as tx:
                repo = EvidenceRepository(tx)
                rows = repo.list_by(prestamo_id=str(loan_id), etapa=stage.value)
                for row in rows:
                    if row["cloudinary_public_id"] == public_id:
                        if row["registrada_por_usuario_id"] != user.user_id:
                            raise HTTPException(409, "Identificador de subida en uso")
                        return row
                allowed = ("RESERVADO",) if stage == EvidenceStage.DELIVERY else ("ACTIVO", "VENCIDO")
                if loan["estado"] not in allowed:
                    raise HTTPException(409, "Estado del préstamo incompatible")
                if sum(r["tipo"] in ("FOTO", "VIDEO") for r in rows) >= 6:
                    raise HTTPException(409, "Máximo seis archivos por etapa")
                storage = CloudinaryStorage()
                asset = storage.upload(data, mime, public_id, folder)
                try:
                    record = repo.add(dict(prestamo_id=str(loan_id), registrada_por_usuario_id=user.user_id,
                                           etapa=stage.value, tipo="VIDEO" if video else "FOTO",
                                           url=asset.url, cloudinary_public_id=asset.public_id,
                                           estado_integracion="COMPLETADA"))
                    tx.commit()
                    # GET_LOCK started an implicit connection transaction; explicitly commit it.
                    connection.commit()
                    return record
                except Exception:
                    tx.rollback()
                    connection.rollback()
                    # A commit failure can be ambiguous; preserve asset for retry/reconciliation.
                    # Do not delete potentially committed evidence.
                    raise
        finally:
            connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})
            connection.rollback()
