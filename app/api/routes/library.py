from fastapi import APIRouter, Query

from app.api.schemas import DeskStateOutput
from app.domain.occupancy import desk_state

router = APIRouter(prefix="/v1/library", tags=["library"])


@router.get("/desk-state", response_model=DeskStateOutput)
def library_desk_state(
    people: int = Query(default=0, ge=0, le=1000),
    objects: int = Query(default=0, ge=0, le=1000),
    unattended_seconds: int = Query(default=0, ge=0, le=86_400),
):
    return {
        "state": desk_state(people, objects, unattended_seconds),
        "is_automatic_release": False,
        "note": "Regla de demostración; validar política institucional y evitar penalizar falsos positivos.",
    }
