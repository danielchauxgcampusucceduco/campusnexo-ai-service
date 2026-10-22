from fastapi import APIRouter, HTTPException

from app.api.schemas import ThermalInput, ThermalRecommendationOutput
from app.domain.thermal import simulate_free_warming

router = APIRouter(prefix="/v1/thermal", tags=["thermal"])


@router.post("/recommendation", response_model=ThermalRecommendationOutput)
def thermal_recommendation(payload: ThermalInput):
    request_values = payload.model_dump(exclude={"horizon_min"})
    request_values["max_minutes"] = payload.horizon_min
    try:
        return simulate_free_warming(**request_values)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
