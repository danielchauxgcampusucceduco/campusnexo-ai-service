from fastapi import FastAPI
from app.api.routes.assignment import router as assignment_router
from app.api.routes.health import router as health_router
from app.api.routes.library import router as library_router
from app.api.routes.occupancy import router as occupancy_router
from app.api.routes.thermal import router as thermal_router
from app.api.routes.vision import router as vision_router

app = FastAPI(title="CampusNexo AI Service", version="0.2.0", description="Estimación de ocupación por fusión heurística (Kalman escalar, no calibrado), conteo YOLO opcional y utilidades académicas; sin control de actuadores.")
app.include_router(health_router)
app.include_router(occupancy_router)
app.include_router(thermal_router)
app.include_router(assignment_router)
app.include_router(library_router)
app.include_router(vision_router)

