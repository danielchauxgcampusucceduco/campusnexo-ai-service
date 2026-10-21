from collections import OrderedDict
from threading import Lock
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from app.domain.occupancy import KalmanOccupancy, desk_state
from app.domain.thermal import simulate_free_warming
from app.domain.assignment import assign_rooms
from app.infrastructure.vision import YoloCounter, VisionUnavailable

vision = YoloCounter()
filters: OrderedDict[str, KalmanOccupancy] = OrderedDict()
filters_lock = Lock()

class OccupancyInput(BaseModel):
    space_id: str = Field(min_length=1, max_length=32)
    yolo_people: int | None = Field(default=None, ge=0, le=1000)
    co2_ppm: float = Field(ge=0, le=10000)
    wifi_devices: int = Field(ge=0, le=10000)
    outdoor_co2_ppm: float = Field(default=415, ge=300, le=1000)
class ThermalInput(BaseModel):
    current_temp_c: float = Field(ge=-20, le=60)
    outside_temp_c: float = Field(ge=-30, le=60)
    occupancy: int = Field(ge=0, le=1000)
    lighting_kw: float = Field(ge=0, le=100)
    resistance_c_per_kw: float = Field(default=2.4, gt=0, le=1000)
    capacitance_kwh_per_c: float = Field(default=1.85, gt=0, le=1000)
    comfort_limit_c: float = Field(default=24.5, ge=10, le=35)
    horizon_min: int = Field(default=20, ge=1, le=120)
class AssignmentInput(BaseModel):
    courses: list[dict]
    rooms: list[dict]
    safety_margin: float = Field(default=1.10, gt=0, le=2)

app = FastAPI(title="CampusNexo AI Service", version="0.2.0", description="Estimación de ocupación por fusión heurística (Kalman escalar, no calibrado), conteo YOLO opcional y utilidades académicas; sin control de actuadores.")

@app.get("/health")
def health(): return {"status": "ok", "vision": "optional; enabled when the vision extra and weights are available"}

@app.post("/v1/occupancy/estimate")
def estimate_occupancy(payload: OccupancyInput):
    with filters_lock:
        estimator = filters.setdefault(payload.space_id, KalmanOccupancy())
        filters.move_to_end(payload.space_id)
        while len(filters) > 2000:
            filters.popitem(last=False)
        estimate, confidence = estimator.update(payload.yolo_people, payload.co2_ppm, payload.wifi_devices, payload.outdoor_co2_ppm)
    return {"space_id": payload.space_id, "occupancy_estimate": estimate, "confidence_pct": confidence,
            "confidence_meaning": "estabilidad interna del filtro (varianza), no probabilidad de acierto",
            "method": "kalman_escalar_pesos_fijos_no_calibrado",
            "camera_available": payload.yolo_people is not None, "is_estimate": True,
            "note": "Heurística con coeficientes iniciales de demostración: no es un modelo entrenado. "
                    "Medir el error con eval/evaluate.py antes de presentar precisión. El estado se reinicia al reiniciar el proceso."}

@app.post("/v1/vision/count")
async def count_people(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Envía el cuerpo binario con Content-Type image/jpeg, image/png o image/webp")
    limit = 8 * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > limit:
        raise HTTPException(413, "Imagen supera 8 MiB")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            chunks.clear()
            raise HTTPException(413, "Imagen supera 8 MiB")
        chunks.append(chunk)
    raw = b"".join(chunks)
    try: return vision.count_people(raw)
    except VisionUnavailable as exc: raise HTTPException(503, str(exc))
    except ValueError as exc: raise HTTPException(400, str(exc))
    finally:
        chunks.clear()
        del raw

@app.post("/v1/thermal/recommendation")
def thermal(payload: ThermalInput):
    try: return simulate_free_warming(**payload.model_dump())
    except ValueError as exc: raise HTTPException(422, str(exc))

@app.post("/v1/rooms/assignment")
def assignment(payload: AssignmentInput):
    try: return assign_rooms(payload.courses, payload.rooms, payload.safety_margin)
    except (ValueError, KeyError, TypeError) as exc: raise HTTPException(422, str(exc))

@app.get("/v1/library/desk-state")
def library_desk_state(people: int = 0, objects: int = 0, unattended_seconds: int = 0):
    if min(people, objects, unattended_seconds) < 0: raise HTTPException(422, "Los parámetros no pueden ser negativos")
    return {"state": desk_state(people, objects, unattended_seconds), "is_automatic_release": False,
            "note": "Regla de demostración; validar política institucional y evitar penalizar falsos positivos."}
