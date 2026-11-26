import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.shared.config import Settings
from app.infrastructure.messaging.relay import relay_loop
from app.infrastructure.messaging.loan_consumer import consume_loans
from app.interfaces.rest.health import router as health_router
from app.interfaces.rest.evidence import router as evidence_router
from app.interfaces.rest.incident import router as incident_router

from app.interfaces.rest.admin_incident import router as admin_incident_router

from app.interfaces.rest.analysis import router as analysis_router
from app.interfaces.rest.internal_incident import router as internal_incident_router

@asynccontextmanager
async def lifespan(app):
    settings = Settings()
    stop = asyncio.Event()
    tasks = []
    if (settings.outbox_publisher_enabled or settings.loan_consumer_enabled) and not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is required when messaging is enabled")
    if settings.outbox_publisher_enabled:
        tasks.append(asyncio.create_task(relay_loop(settings, stop)))
    if settings.loan_consumer_enabled:
        tasks.append(asyncio.create_task(consume_loans(settings, stop)))
    try:
        yield
    finally:
        stop.set()
        if tasks:
            await asyncio.gather(*tasks)


app = FastAPI(
    lifespan=lifespan,
    title="LendUp Evidence and Incident Service",
    description="Evidence management, incident resolution and assisted image analysis.",
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(evidence_router)
app.include_router(incident_router)
app.include_router(admin_incident_router)
app.include_router(analysis_router)
app.include_router(internal_incident_router)
