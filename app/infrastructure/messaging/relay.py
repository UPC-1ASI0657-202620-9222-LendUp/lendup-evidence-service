import asyncio
import logging

from sqlalchemy.orm import Session

from app.infrastructure.messaging.outbox import next_event, mark_failure, mark_published
from app.infrastructure.messaging.publisher import publish_event
from app.infrastructure.persistence.database import get_engine

logger = logging.getLogger(__name__)


def relay_once(settings):
    # The row stays locked until confirmation/failure is persisted.
    # Run this bounded operation in a worker thread, not the API event loop.
    with Session(get_engine()) as session:
        row = next_event(session)
        if row is None:
            session.rollback()
            return False
        try:
            asyncio.run(publish_event(settings, row))
        except Exception as exc:
            mark_failure(session, row, exc)
            logger.warning("Outbox publication failed: %s (%s)", row["id"], type(exc).__name__)
        else:
            mark_published(session, row)
        session.commit()
        return True


async def relay_loop(settings, stop: asyncio.Event):
    while not stop.is_set():
        try:
            processed = await asyncio.to_thread(relay_once, settings)
        except Exception as exc:
            logger.warning("Outbox relay unavailable: %s", type(exc).__name__)
            processed = False
        if not processed:
            try:
                await asyncio.wait_for(stop.wait(), timeout=2)
            except TimeoutError:
                pass
