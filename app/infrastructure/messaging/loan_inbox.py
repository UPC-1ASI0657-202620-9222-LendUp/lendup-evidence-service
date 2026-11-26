"""Commit deduplication and projection together before acknowledging."""
from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.events.loan_events import IDS, projection_changes, validate_event
from app.infrastructure.persistence.database import get_engine
from app.infrastructure.persistence.models import inbox_events, loan_projection


def process_loan_event(route, raw):
    event = validate_event(route, raw)
    p = event["payload"]
    with Session(get_engine()) as session, session.begin():
        try:
            with session.begin_nested():
                session.execute(inbox_events.insert().values(
                    id=event["event_id"], aggregate_id=event["aggregate_id"],
                    aggregate_version=event["aggregate_version"], routing_key=route))
        except IntegrityError as exc:
            if getattr(exc.orig, "args", (None,))[0] != 1062:
                raise
            return False
        seed = insert(loan_projection).values(**{field: p[field] for field in IDS})
        session.execute(seed.on_duplicate_key_update(prestamo_id=loan_projection.c.prestamo_id))
        row = session.execute(select(loan_projection).where(
            loan_projection.c.prestamo_id == p["prestamo_id"]).with_for_update()).mappings().one()
        changes = projection_changes(row, event)
        if changes:
            session.execute(update(loan_projection).where(
                loan_projection.c.prestamo_id == p["prestamo_id"]).values(**changes))
    return True
