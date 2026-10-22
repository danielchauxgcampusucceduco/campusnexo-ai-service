from fastapi import APIRouter, HTTPException

from app.api.schemas import AssignmentInput, AssignmentOutput
from app.domain.assignment import assign_rooms

router = APIRouter(prefix="/v1/rooms", tags=["assignment"])


@router.post("/assignment", response_model=AssignmentOutput, response_model_exclude_none=True)
def assign_course_rooms(payload: AssignmentInput):
    courses = [course.model_dump() for course in payload.courses]
    rooms = [room.model_dump() for room in payload.rooms]
    try:
        return assign_rooms(courses, rooms, payload.safety_margin)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
