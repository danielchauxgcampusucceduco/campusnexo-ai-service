from fastapi import FastAPI

from app.api.routes.assignment import router as assignment_router
from app.api.routes.health import router as health_router
from app.api.routes.library import router as library_router
from app.api.routes.occupancy import router as occupancy_router
from app.api.routes.thermal import router as thermal_router
from app.api.routes.vision import router as vision_router
from app.infrastructure.occupancy_registry import OccupancyFilterRegistry
from app.infrastructure.request_context import request_context
from app.infrastructure.vision import YoloCounter


def create_app(
    occupancy_registry: OccupancyFilterRegistry | None = None,
    vision_counter: YoloCounter | None = None,
) -> FastAPI:
    application = FastAPI(
        title="CampusNexo AI Service",
        version="0.2.0",
        description=(
            "Estimación de ocupación por fusión heurística (Kalman escalar, no calibrado), "
            "conteo YOLO opcional y utilidades académicas; sin control de actuadores."
        ),
    )
    application.state.occupancy_registry = (
        occupancy_registry if occupancy_registry is not None else OccupancyFilterRegistry()
    )
    application.state.vision_counter = vision_counter if vision_counter is not None else YoloCounter()
    application.middleware("http")(request_context)
    for router in (
        health_router,
        occupancy_router,
        thermal_router,
        assignment_router,
        library_router,
        vision_router,
    ):
        application.include_router(router)
    return application
