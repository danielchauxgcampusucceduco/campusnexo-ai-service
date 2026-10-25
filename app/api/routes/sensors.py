from fastapi import APIRouter

from app.api.schemas import AnomaliesInput, AnomaliesOutput
from app.domain.anomalias import Lectura, detectar

router = APIRouter(prefix="/v1/sensors", tags=["sensors"])


@router.post("/anomalies", response_model=AnomaliesOutput)
def sensor_anomalies(payload: AnomaliesInput):
    lecturas = [Lectura(reading.space_id.strip(), reading.timestamp,
                        reading.model_dump(include={"co2_ppm", "temperature_c", "humidity_pct", "illuminance_lux",
                                                    "active_power_kw"}))
                for reading in payload.readings]
    return {
        "anomalies": [{"space_id": a.space_id, "sensor": a.sensor, "timestamp": a.timestamp, "kind": a.tipo,
                       "value": a.valor, "detail": a.detalle} for a in detectar(lecturas)],
        "readings_analyzed": len(lecturas),
        "method": "rango_fisico_valor_pegado_salto_mad",
    }
