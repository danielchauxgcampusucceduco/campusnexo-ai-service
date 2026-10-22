from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_vision_counter
from app.infrastructure.vision import VisionUnavailable, YoloCounter
from app.settings import MAX_VISION_IMAGE_BYTES

router = APIRouter(prefix="/v1/vision", tags=["vision"])
ACCEPTED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@router.post("/count")
async def count_people(request: Request, vision: YoloCounter = Depends(get_vision_counter)):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in ACCEPTED_IMAGE_TYPES:
        raise HTTPException(415, "Envía el cuerpo binario con Content-Type image/jpeg, image/png o image/webp")
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_VISION_IMAGE_BYTES:
        raise HTTPException(413, "Imagen supera 8 MiB")

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_VISION_IMAGE_BYTES:
            chunks.clear()
            raise HTTPException(413, "Imagen supera 8 MiB")
        chunks.append(chunk)
    raw = b"".join(chunks)
    try:
        return vision.count_people(raw)
    except VisionUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        chunks.clear()
        del raw
