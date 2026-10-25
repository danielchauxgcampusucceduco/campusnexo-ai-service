from zoneinfo import ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException

from app.api.schemas import ForecastInput, ForecastOutput
from app.domain.pronostico import pronosticar

router = APIRouter(prefix="/v1/occupancy", tags=["forecast"])


@router.post("/forecast", response_model=ForecastOutput)
def occupancy_forecast(payload: ForecastInput):
    try:
        resultado = pronosticar([(sample.timestamp, sample.people) for sample in payload.history],
                                payload.capacity, payload.horizon_hours, payload.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(422, f"Zona horaria desconocida: {payload.timezone}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "space_id": payload.space_id.strip(),
        "method": resultado.metodo,
        "samples_used": resultado.muestras,
        "points": [{"timestamp": p.timestamp, "people": p.people, "low": p.low, "high": p.high}
                   for p in resultado.puntos],
        "note": "Perfil semanal aprendido del historial del salón; el intervalo es aproximado (≈80 %).",
    }
