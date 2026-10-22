from fastapi import APIRouter, Depends

from app.api.dependencies import get_occupancy_registry
from app.api.schemas import (
    OccupancyBatchInput,
    OccupancyBatchOutput,
    OccupancyEstimateOutput,
    OccupancyInput,
)
from app.infrastructure.occupancy_registry import OccupancyFilterRegistry

router = APIRouter(prefix="/v1/occupancy", tags=["occupancy"])


@router.post("/estimate", response_model=OccupancyEstimateOutput)
def estimate_occupancy(
    payload: OccupancyInput,
    occupancy_filters: OccupancyFilterRegistry = Depends(get_occupancy_registry),
):
    return _estimate(payload, occupancy_filters)


@router.post("/estimate/batch", response_model=OccupancyBatchOutput)
def estimate_occupancy_batch(
    payload: OccupancyBatchInput,
    occupancy_filters: OccupancyFilterRegistry = Depends(get_occupancy_registry),
):
    return {"estimates": [_estimate(item, occupancy_filters) for item in payload.measurements]}


def _estimate(payload: OccupancyInput, occupancy_filters: OccupancyFilterRegistry) -> dict:
    estimate, confidence = occupancy_filters.estimate(
        payload.space_id, payload.yolo_people, payload.co2_ppm, payload.wifi_devices, payload.outdoor_co2_ppm
    )
    return {
        "space_id": payload.space_id,
        "occupancy_estimate": estimate,
        "confidence_pct": confidence,
        "confidence_meaning": "estabilidad interna del filtro (varianza), no probabilidad de acierto",
        "method": "kalman_escalar_pesos_fijos_no_calibrado",
        "camera_available": payload.yolo_people is not None,
        "is_estimate": True,
        "note": "Heurística con coeficientes iniciales de demostración: no es un modelo entrenado. "
                "Medir el error con eval/evaluate.py antes de presentar precisión. El estado se reinicia al reiniciar el proceso.",
    }
