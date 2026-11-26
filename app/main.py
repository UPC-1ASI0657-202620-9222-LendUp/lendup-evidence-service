import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.shared.config import Settings
from app.infrastructure.messaging.relay import relay_loop
from app.interfaces.rest.health import router as health_router
from app.interfaces.rest.evidence import router as evidence_router
from app.interfaces.rest.incident import router as incident_router

from app.interfaces.rest.admin_incident import router as admin_incident_router

from app.interfaces.rest.analysis import router as analysis_router

@asynccontextmanager
async def lifespan(app):
    settings = Settings()
    stop = asyncio.Event()
    task = None
    if settings.outbox_publisher_enabled:
        if not settings.rabbitmq_url:
            raise RuntimeError("RABBITMQ_URL is required when the outbox publisher is enabled")
        task = asyncio.create_task(relay_loop(settings, stop))
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            await task


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
