from fastapi import APIRouter, Query

from app.api.schemas import DeskStateOutput
from app.domain.occupancy import desk_state
from app.settings import MAX_DESK_COUNT, MAX_UNATTENDED_SECONDS

router = APIRouter(prefix="/v1/library", tags=["library"])


@router.get("/desk-state", response_model=DeskStateOutput)
def library_desk_state(
    people: int = Query(default=0, ge=0, le=MAX_DESK_COUNT),
    objects: int = Query(default=0, ge=0, le=MAX_DESK_COUNT),
    unattended_seconds: int = Query(default=0, ge=0, le=MAX_UNATTENDED_SECONDS),
):
    return {
        "state": desk_state(people, objects, unattended_seconds),
        "is_automatic_release": False,
        "note": "Regla de demostración; validar política institucional y evitar penalizar falsos positivos.",
    }
