from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select, update, exists
from sqlalchemy.orm import Session

from app.domain.events.events import ROUTES
from app.infrastructure.persistence.models import outbox_events


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def enqueue(session: Session, event: dict):
    """Caller commits the business write and event together."""
    now = utc_now()
    session.execute(insert(outbox_events).values(
        id=event["event_id"], aggregate_id=event["aggregate_id"],
        aggregate_version=event["aggregate_version"], routing_key=ROUTES[event["event_type"]],
        envelope=event, mandatory=event["event_type"] != "EvidenciaRegistrada",
        created_at=now, next_attempt_at=now, attempts=0))


def next_event(session: Session):
    older = outbox_events.alias("older")
    prior = exists(select(older.c.id).where(
        older.c.aggregate_id == outbox_events.c.aggregate_id,
        older.c.aggregate_version < outbox_events.c.aggregate_version,
        older.c.published_at.is_(None))).correlate(outbox_events)
    statement = (select(outbox_events)
                 .where(outbox_events.c.published_at.is_(None),
                        outbox_events.c.next_attempt_at <= utc_now(), ~prior)
                 .order_by(outbox_events.c.created_at, outbox_events.c.id)
                 .limit(1).with_for_update(skip_locked=True))
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def retry_delay(attempts):
    return min(300, 2 ** min(max(attempts, 1), 9))


def mark_failure(session, row, error):
    attempts = row["attempts"] + 1
    session.execute(update(outbox_events).where(outbox_events.c.id == row["id"]).values(
        attempts=attempts, last_error=type(error).__name__[:255],
        next_attempt_at=utc_now() + timedelta(seconds=retry_delay(attempts))))


def mark_published(session, row):
    session.execute(update(outbox_events).where(outbox_events.c.id == row["id"]).values(
        published_at=utc_now(), attempts=row["attempts"] + 1, last_error=None))
