"""Asignación óptima exacta por programación dinámica para instancias pequeñas."""
from functools import lru_cache
import math

from app.settings import MAX_ASSIGNMENT_COURSES


def assign_rooms(courses: list[dict], rooms: list[dict], safety_margin: float = 1.10) -> dict:
    if len(courses) > MAX_ASSIGNMENT_COURSES:
        raise ValueError(
            f"La demo exacta admite hasta {MAX_ASSIGNMENT_COURSES} cursos; "
            "use un solver MILP para instancias mayores"
        )
    if not 0 < safety_margin <= 2:
        raise ValueError("safety_margin fuera de rango")
    course_ids: set[str] = set()
    for course in courses:
        course_id = course.get("course_id")
        attendance = course.get("attendance")
        if not isinstance(course_id, str) or not course_id.strip() or course_id in course_ids:
            raise ValueError("course_id debe ser único y no vacío")
        if isinstance(attendance, bool) or not isinstance(attendance, int) or attendance < 0:
            raise ValueError(f"attendance inválido para {course_id}")
        course_ids.add(course_id)
    room_ids: set[str] = set()
    for room in rooms:
        room_id = room.get("room_id")
        capacity = room.get("capacity")
        power = room.get("power_kw")
        if not isinstance(room_id, str) or not room_id.strip() or room_id in room_ids:
            raise ValueError("room_id debe ser único y no vacío")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError(f"capacity inválida para {room_id}")
        if isinstance(power, bool) or not isinstance(power, (int, float)) or not math.isfinite(power) or power < 0:
            raise ValueError(f"power_kw inválida para {room_id}")
        room_ids.add(room_id)
    if len(rooms) < len(courses):
        return {"feasible": False, "assignments": [], "reason": "No hay suficientes salones disponibles."}
    # El coste minimiza potencia nominal ponderada. Toda sala ha de cumplir capacidad mínima.
    @lru_cache(None)
    def best(index: int, used: int):
        if index == len(courses): return (0.0, ())
        course = courses[index]
        seats = int(course["attendance"])
        options = []
        for room_index, room in enumerate(rooms):
            if used & (1 << room_index) or room["capacity"] < seats * safety_margin:
                continue
            tail = best(index + 1, used | (1 << room_index))
            if tail is not None:
                options.append((float(room["power_kw"]) + tail[0], (room_index,) + tail[1]))
        return min(options, key=lambda x: x[0]) if options else None
    result = best(0, 0)
    if result is None:
        return {"feasible": False, "assignments": [], "reason": "No existe una asignación que cumpla el margen de capacidad."}
    choices = result[1]
    assignments = []
    for course, room_index in zip(courses, choices):
        room = rooms[room_index]
        assignments.append({"course_id": course["course_id"], "room_id": room["room_id"],
                            "attendance": course["attendance"], "capacity": room["capacity"],
                            "utilization_pct": round(course["attendance"] / room["capacity"] * 100, 1),
                            "nominal_power_kw": room["power_kw"]})
    return {"feasible": True, "assignments": assignments, "total_nominal_power_kw": round(result[0], 3),
            "objective": "minimize_sum_of_nominal_power", "note": "Optimización académica; valida horarios, distancias y accesibilidad antes de aplicar."}
