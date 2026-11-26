import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.infrastructure.clients.loans import participant_loan
from app.infrastructure.gemini.adapter import GoogleAIAdapter
from app.infrastructure.gemini.circuit_breaker import CircuitOpenError
from app.infrastructure.persistence.database import get_engine
from app.infrastructure.persistence.models import analyses
from app.infrastructure.persistence.repositories import AnalysisRepository, EvidenceRepository, IncidentRepository
from app.shared.security import Principal

logger = logging.getLogger(__name__)


def validate_pair(initial, final, loan_id: UUID):
    for record, stage in ((initial, "ENTREGA"), (final, "DEVOLUCION")):
        if (not record or record["prestamo_id"] != str(loan_id)
                or record["etapa"] != stage or record["tipo"] != "FOTO"
                or record["estado_integracion"] != "COMPLETADA"
                or not record.get("url") or not record.get("cloudinary_public_id")):
            raise HTTPException(400, "Se requieren fotografías verificadas de entrega y devolución del mismo préstamo")


def request_analysis(session: Session, loan_id: UUID, user: Principal, body: dict):
    participant_loan(loan_id, user)
    repo = EvidenceRepository(session)
    initial = repo.get(str(body["evidencia_inicial_id"]))
    final = repo.get(str(body["evidencia_final_id"]))
    validate_pair(initial, final, loan_id)
    incident_id = body.get("incidencia_id")
    if incident_id:
        incident = IncidentRepository(session).get(str(incident_id))
        if not incident or incident["prestamo_id"] != str(loan_id):
            raise HTTPException(400, "Incidencia incompatible")
        if incident["estado"] == "RESUELTA":
            raise HTTPException(409, "Incidencia resuelta")
    record = AnalysisRepository(session).add(dict(
        prestamo_id=str(loan_id), evidencia_inicial_id=str(body["evidencia_inicial_id"]),
        evidencia_final_id=str(body["evidencia_final_id"]),
        incidencia_id=str(incident_id) if incident_id else None,
        solicitado_por_usuario_id=user.user_id, estado="PENDIENTE"))
    session.commit()
    return record


def read_analysis(session: Session, loan_id: UUID, analysis_id: UUID, user: Principal):
    participant_loan(loan_id, user)
    record = AnalysisRepository(session).get(str(analysis_id))
    if not record or record["prestamo_id"] != str(loan_id):
        raise HTTPException(404, "Análisis no encontrado")
    return record


def claim_analysis(analysis_id: str):
    with Session(get_engine()) as session:
        result = session.execute(update(analyses).where(
            analyses.c.id == analysis_id, analyses.c.estado == "PENDIENTE"
        ).values(estado="PROCESANDO"))
        if result.rowcount != 1:
            session.rollback()
            return None
        row = AnalysisRepository(session).get(analysis_id)
        repo = EvidenceRepository(session)
        initial = repo.get(row["evidencia_inicial_id"])
        final = repo.get(row["evidencia_final_id"])
        session.commit()
        return row, initial, final


def finish_analysis(analysis_id: str, values: dict):
    with Session(get_engine()) as session:
        session.execute(update(analyses).where(
            analyses.c.id == analysis_id, analyses.c.estado == "PROCESANDO"
        ).values(**values, completado_en=datetime.now(timezone.utc).replace(tzinfo=None)))
        session.commit()


async def process_analysis(analysis_id: str):
    from starlette.concurrency import run_in_threadpool
    try:
        claimed = await run_in_threadpool(claim_analysis, analysis_id)
        if claimed is None:
            return
        row, initial, final = claimed
        try:
            validate_pair(initial, final, UUID(row["prestamo_id"]))
            result = await GoogleAIAdapter().compare(initial["url"], final["url"])
            values = dict(estado="COMPLETADO", resultado_resumen=result.resumen,
                          resultado_detalle={**result.model_dump(), "requiere_revision_humana": True},
                          error_descripcion=None)
        except CircuitOpenError:
            values = dict(estado="FALLIDO", error_descripcion="Gemini temporalmente no disponible; reintenta más tarde",
                          resultado_resumen=None, resultado_detalle=None)
        except Exception as exc:
            logger.warning("Evidence analysis failed: %s (%s)", analysis_id, type(exc).__name__)
            values = dict(estado="FALLIDO", error_descripcion="No se pudo completar el análisis asistido",
                          resultado_resumen=None, resultado_detalle=None)
        await run_in_threadpool(finish_analysis, analysis_id, values)
    except Exception as exc:
        logger.error("Analysis persistence failed: %s (%s)", analysis_id, type(exc).__name__)
