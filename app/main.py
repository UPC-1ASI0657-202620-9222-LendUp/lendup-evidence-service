from fastapi import FastAPI
from app.interfaces.rest.health import router as health_router
from app.interfaces.rest.evidence import router as evidence_router
from app.interfaces.rest.incident import router as incident_router

from app.interfaces.rest.admin_incident import router as admin_incident_router

app = FastAPI(
    title="LendUp Evidence and Incident Service",
    description="Evidence management, incident resolution and assisted image analysis.",
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(evidence_router)
app.include_router(incident_router)
app.include_router(admin_incident_router)
