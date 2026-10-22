from fastapi import APIRouter, HTTPException

from app.api.schemas import DeskStateOutput
from app.domain.occupancy import desk_state

router = APIRouter(prefix="/v1/library", tags=["library"])


@router.get("/desk-state", response_model=DeskStateOutput)
def library_desk_state(people: int = 0, objects: int = 0, unattended_seconds: int = 0):
    if min(people, objects, unattended_seconds) < 0:
        raise HTTPException(422, "Los parámetros no pueden ser negativos")
    return {
        "state": desk_state(people, objects, unattended_seconds),
        "is_automatic_release": False,
        "note": "Regla de demostración; validar política institucional y evitar penalizar falsos positivos.",
    }
