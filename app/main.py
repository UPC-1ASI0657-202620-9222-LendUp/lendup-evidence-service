from fastapi import FastAPI
from app.interfaces.rest.health import router

app = FastAPI(
    title="LendUp Evidence and Incident Service",
    description="Evidence management, incident resolution and assisted image analysis.",
    version="0.1.0",
)
app.include_router(router)
