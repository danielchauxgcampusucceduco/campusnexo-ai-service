from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    OccupancyBatchInput,
    OccupancyBatchOutput,
    OccupancyEstimateOutput,
    OccupancyInput,
)
from app.domain.occupancy import fuse_occupancy

router = APIRouter(prefix="/v1/occupancy", tags=["occupancy"])

METHOD = "fusion_varianza_inversa_no_calibrada"
CONFIDENCE_MEANING = "1 − σ/capacidad: margen de error relativo al tamaño del salón, no probabilidad de acierto"
NOTE = ("Mismo modelo de fusión que el gemelo digital, con parámetros ilustrativos: no es un modelo entrenado. "
        "Medir el error con eval/evaluate.py antes de presentar precisión.")


@router.post("/estimate", response_model=OccupancyEstimateOutput)
def estimate_occupancy(payload: OccupancyInput):
    return _estimate(payload)


@router.post("/estimate/batch", response_model=OccupancyBatchOutput)
def estimate_occupancy_batch(payload: OccupancyBatchInput):
    return {"estimates": [_estimate(item) for item in payload.measurements]}


def _estimate(payload: OccupancyInput) -> dict:
    try:
        fusion = fuse_occupancy(payload.yolo_people, payload.co2_ppm, payload.wifi_devices, payload.area_sqm,
                                payload.outdoor_co2_ppm)
    except ValueError as invalid:
        raise HTTPException(status_code=422, detail=str(invalid)) from invalid
    return {
        "space_id": payload.space_id,
        "occupancy_estimate": min(fusion.people(), payload.capacity * 3),
        "confidence_pct": fusion.confidence_pct(payload.capacity),
        "sigma_people": round(fusion.sigma, 3),
        "confidence_meaning": CONFIDENCE_MEANING,
        "method": METHOD,
        "camera_available": payload.yolo_people is not None,
        "is_estimate": True,
        "sources": [{"source": s.source, "people": s.people, "variance": s.variance, "weight": s.weight}
                    for s in fusion.sources],
        "note": NOTE,
    }
