from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import CapabilitiesOutput
from app.settings import (
    MAX_ANOMALY_READINGS,
    MAX_ASSIGNMENT_COURSES,
    MAX_ASSIGNMENT_ROOMS,
    MAX_ASSIGNMENT_ATTENDANCE,
    MAX_FORECAST_HISTORY,
    MAX_FORECAST_HOURS,
    MAX_OCCUPANCY_BATCH_ITEMS,
    MAX_ROOM_CAPACITY,
    MAX_ROOM_POWER_KW,
    MAX_VISION_IMAGE_BYTES,
)

router = APIRouter(tags=["health", "capabilities"])


@router.get("/health")
def health():
    return {"status": "ok", "vision": "optional; enabled when the vision extra and weights are available"}


@router.get("/ready")
def readiness(request: Request):
    """Report whether required in-process adapters were initialized for traffic."""
    required = ("vision_counter",)
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
            {"name": "occupancy", "mode": "fusion_varianza_inversa_no_calibrada",
             "summary": "Fusión sin estado de cámara opcional, CO2 y Wi-Fi con el modelo del gemelo; "
                        "confidence_pct no es probabilidad."},
            {"name": "occupancy_batch", "mode": "stateless_fusion_per_reading",
             "summary": "Procesa en una petición varias lecturas; cada una se fusiona por separado."},
            {"name": "room_assignment", "mode": "exact_rectangular_matching",
             "summary": "Minimiza potencia nominal para instancias pequeñas."},
            {"name": "vision", "mode": "optional_yolo",
             "summary": "Conteo disponible solo si el extra de visión y sus pesos están configurados."},
            {"name": "sensor_anomalies", "mode": "rango_fisico_valor_pegado_salto_mad",
             "summary": "Señala lecturas imposibles, sensores pegados y saltos bruscos; no corrige datos."},
            {"name": "occupancy_forecast", "mode": "perfil_semanal_suavizado",
             "summary": "Pronóstico por franja horaria aprendido del historial del salón; sin estado."},
        ],
        "limits": {
            "occupancy_batch_items": MAX_OCCUPANCY_BATCH_ITEMS,
            "assignment_courses": MAX_ASSIGNMENT_COURSES,
            "assignment_rooms": MAX_ASSIGNMENT_ROOMS,
            "course_attendance": MAX_ASSIGNMENT_ATTENDANCE,
            "room_capacity": MAX_ROOM_CAPACITY,
            "room_power_kw": MAX_ROOM_POWER_KW,
            "vision_image_bytes": MAX_VISION_IMAGE_BYTES,
            "anomaly_readings": MAX_ANOMALY_READINGS,
            "forecast_history": MAX_FORECAST_HISTORY,
            "forecast_hours": MAX_FORECAST_HOURS,
        },
    }
