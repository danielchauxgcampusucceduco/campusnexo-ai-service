import os

from fastapi import Depends, FastAPI

from app.api.routes.assignment import router as assignment_router
from app.api.routes.health import router as health_router
from app.api.routes.library import router as library_router
from app.api.routes.occupancy import router as occupancy_router
from app.api.routes.thermal import router as thermal_router
from app.api.routes.vision import router as vision_router
from app.infrastructure.api_key import require_api_key
from app.infrastructure.request_context import request_context
from app.infrastructure.vision import YoloCounter

MIN_API_KEY_LENGTH = 24


def create_app(vision_counter: YoloCounter | None = None, api_key: str | None = None) -> FastAPI:
    """Builds the service. ``api_key`` defaults to the ``AI_API_KEY`` environment variable."""
    key = api_key if api_key is not None else os.environ.get("AI_API_KEY", "")
    if key and len(key) < MIN_API_KEY_LENGTH:
        raise ValueError(f"AI_API_KEY debe tener al menos {MIN_API_KEY_LENGTH} caracteres")
    application = FastAPI(
        title="CampusNexo AI Service",
        version="0.3.0",
        description=(
            "Estimación de ocupación sin estado con el mismo modelo de fusión que el gemelo digital "
            "(cámara, balance de CO2 y Wi-Fi), conteo YOLO opcional y utilidades académicas; sin control de "
            "actuadores."
        ),
    )
    application.state.vision_counter = vision_counter if vision_counter is not None else YoloCounter()
    application.state.api_key = key
    application.middleware("http")(request_context)
    application.include_router(health_router)
    protected = [Depends(require_api_key)]
    for router in (occupancy_router, thermal_router, assignment_router, library_router, vision_router):
        application.include_router(router, dependencies=protected)
    return application
