from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import CapabilitiesOutput
from app.settings import (
    MAX_ASSIGNMENT_COURSES,
    MAX_OCCUPANCY_BATCH_ITEMS,
    MAX_THERMAL_HORIZON_MINUTES,
    MAX_TRACKED_SPACES,
    MAX_VISION_IMAGE_BYTES,
)

router = APIRouter(tags=["health", "capabilities"])


@router.get("/health")
def health():
    return {"status": "ok", "vision": "optional; enabled when the vision extra and weights are available"}


@router.get("/ready")
def readiness(request: Request):
    """Report whether required in-process adapters were initialized for traffic."""
    required = ("occupancy_registry", "vision_counter")
    missing = [name for name in required if getattr(request.app.state, name, None) is None]
    if missing:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "missing": missing})
    return {"status": "ready", "optional_features": {"vision": "may be unavailable without model weights"}}


@router.get("/v1/capabilities", response_model=CapabilitiesOutput)
def capabilities():
    return {
        "service": "CampusNexo AI Service",
        "api_version": "v1",
        "features": [
            {"name": "occupancy", "mode": "kalman_escalar_pesos_fijos_no_calibrado",
             "summary": "Estimación con cámara opcional, CO2 y Wi-Fi; confidence_pct no es probabilidad."},
            {"name": "occupancy_batch", "mode": "independent_kalman_per_space",
             "summary": "Procesa en una petición varias lecturas, con filtros independientes por espacio."},
            {"name": "thermal", "mode": "1R1C_exact_exponential",
             "summary": "Proyección térmica académica; no acciona equipos."},
            {"name": "room_assignment", "mode": "exact_dynamic_programming",
             "summary": "Minimiza potencia nominal para instancias pequeñas."},
            {"name": "vision", "mode": "optional_yolo",
             "summary": "Conteo disponible solo si el extra de visión y sus pesos están configurados."},
            {"name": "library_desk_state", "mode": "demonstration_rule",
             "summary": "Recomienda estados de mesa; no libera puestos automáticamente."},
        ],
        "limits": {
            "tracked_spaces": MAX_TRACKED_SPACES,
            "occupancy_batch_items": MAX_OCCUPANCY_BATCH_ITEMS,
            "assignment_courses": MAX_ASSIGNMENT_COURSES,
            "vision_image_bytes": MAX_VISION_IMAGE_BYTES,
            "thermal_horizon_minutes": MAX_THERMAL_HORIZON_MINUTES,
        },
    }
