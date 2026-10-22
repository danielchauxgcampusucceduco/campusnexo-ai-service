from fastapi import FastAPI, HTTPException, Request
from app.api.routes.assignment import router as assignment_router
from app.api.routes.health import router as health_router
from app.api.routes.library import router as library_router
from app.api.routes.occupancy import router as occupancy_router
from app.api.routes.thermal import router as thermal_router
from app.infrastructure.vision import YoloCounter, VisionUnavailable
from app.settings import MAX_VISION_IMAGE_BYTES

vision = YoloCounter()

app = FastAPI(title="CampusNexo AI Service", version="0.2.0", description="Estimación de ocupación por fusión heurística (Kalman escalar, no calibrado), conteo YOLO opcional y utilidades académicas; sin control de actuadores.")
app.include_router(health_router)
app.include_router(occupancy_router)
app.include_router(thermal_router)
app.include_router(assignment_router)
app.include_router(library_router)

@app.post("/v1/vision/count")
async def count_people(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Envía el cuerpo binario con Content-Type image/jpeg, image/png o image/webp")
    limit = MAX_VISION_IMAGE_BYTES
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

