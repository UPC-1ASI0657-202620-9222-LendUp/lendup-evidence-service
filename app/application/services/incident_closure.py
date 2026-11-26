from typing import NamedTuple
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import incident_closures, incidents
from app.infrastructure.clients.loans import loan_accepts_reports


class ReportAdmission(NamedTuple):
    sealed: bool
    generation: str | None


def lock_report_admission(session: Session, loan_id: UUID) -> ReportAdmission:
    key = str(loan_id)
    seed = insert(incident_closures).values(prestamo_id=key)
    session.execute(seed.on_duplicate_key_update(prestamo_id=incident_closures.c.prestamo_id))
    row = session.execute(select(incident_closures.c.sellado, incident_closures.c.sello_id)
                          .where(incident_closures.c.prestamo_id == key).with_for_update()).one()
    return ReportAdmission(row.sellado, row.sello_id)


def reconcile_report_admission(session: Session, loan_id: UUID, observed: ReportAdmission) -> None:
    # Release the Evidence lock before asking Loans for its committed decision under the loan lock.
    session.rollback()
    if not loan_accepts_reports(loan_id):
        raise HTTPException(409, "El préstamo está cerrado")
    current = lock_report_admission(session, loan_id)
    if current.sealed:
        if current != observed:
            raise HTTPException(409, "El cierre del préstamo cambió; reintenta el reporte")
        session.execute(incident_closures.update().where(incident_closures.c.prestamo_id == str(loan_id))
                        .values(sellado=False, sello_id=None))


def close_report_admission(session: Session, loan_id: UUID) -> list[str]:
    lock_report_admission(session, loan_id)
    rows = session.execute(
        select(incidents.c.id, incidents.c.estado).where(incidents.c.prestamo_id == str(loan_id))
        .order_by(incidents.c.id).with_for_update()
    ).all()
    if any(row.estado != "RESUELTA" for row in rows):
        raise HTTPException(409, "Quedan incidencias abiertas")
    session.execute(incident_closures.update()
                    .where(incident_closures.c.prestamo_id == str(loan_id)).values(sellado=True, sello_id=str(uuid4())))
    session.commit()
    return [row.id for row in rows]
