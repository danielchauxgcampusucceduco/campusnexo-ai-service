"""Asignación óptima exacta mediante matching rectangular de coste mínimo."""
import math

from app.settings import (
    MAX_ASSIGNMENT_ATTENDANCE,
    MAX_ASSIGNMENT_COURSES,
    MAX_ASSIGNMENT_ROOMS,
    MAX_ROOM_CAPACITY,
    MAX_ROOM_POWER_KW,
)


def assign_rooms(courses: list[dict], rooms: list[dict], safety_margin: float = 1.10) -> dict:
    if len(courses) > MAX_ASSIGNMENT_COURSES:
        raise ValueError(
            f"La demo exacta admite hasta {MAX_ASSIGNMENT_COURSES} cursos; "
            "use un solver MILP para instancias mayores"
        )
    if len(rooms) > MAX_ASSIGNMENT_ROOMS:
        raise ValueError(f"La demo admite hasta {MAX_ASSIGNMENT_ROOMS} salones")
    if isinstance(safety_margin, bool) or not isinstance(safety_margin, (int, float)) \
            or not math.isfinite(safety_margin) or not 0 < safety_margin <= 2:
        raise ValueError("safety_margin fuera de rango")
    course_ids: set[str] = set()
    normalized_courses = []
    for course in courses:
        if not isinstance(course, dict):
            raise ValueError("course debe ser un registro")
        course_id = course.get("course_id")
        attendance = course.get("attendance")
        if not isinstance(course_id, str) or not course_id.strip() or course_id.strip() in course_ids:
            raise ValueError("course_id debe ser único y no vacío")
        if isinstance(attendance, bool) or not isinstance(attendance, int) \
                or not 0 <= attendance <= MAX_ASSIGNMENT_ATTENDANCE:
            raise ValueError(f"attendance inválido para {course_id}")
        course_id = course_id.strip()
        course_ids.add(course_id)
        normalized_courses.append(course | {"course_id": course_id})
    room_ids: set[str] = set()
    normalized_rooms = []
    for room in rooms:
        if not isinstance(room, dict):
            raise ValueError("room debe ser un registro")
        room_id = room.get("room_id")
        capacity = room.get("capacity")
        power = room.get("power_kw")
        if not isinstance(room_id, str) or not room_id.strip() or room_id.strip() in room_ids:
            raise ValueError("room_id debe ser único y no vacío")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or not 1 <= capacity <= MAX_ROOM_CAPACITY:
            raise ValueError(f"capacity inválida para {room_id}")
        if isinstance(power, bool) or not isinstance(power, (int, float)) or not math.isfinite(power) \
                or not 0 <= power <= MAX_ROOM_POWER_KW:
            raise ValueError(f"power_kw inválida para {room_id}")
        room_id = room_id.strip()
        room_ids.add(room_id)
        normalized_rooms.append(room | {"room_id": room_id})
    courses = normalized_courses
    rooms = normalized_rooms
    if len(rooms) < len(courses):
        return {"feasible": False, "assignments": [], "reason": "No hay suficientes salones disponibles."}
    # Rectangular Hungarian algorithm: O(courses² × rooms), bounded by the small course limit.
    # Ineligible room-course pairs have infinite cost and can never be selected.
    course_count, room_count = len(courses), len(rooms)
    feasible = True
    if course_count == 0:
        choices: tuple[int, ...] = ()
    else:
        costs = [
            [float(room["power_kw"]) if room["capacity"] >= course["attendance"] * safety_margin else math.inf
             for room in rooms]
            for course in courses
        ]
        row_potential = [0.0] * (course_count + 1)
        column_potential = [0.0] * (room_count + 1)
        matched_row = [0] * (room_count + 1)
        previous_column = [0] * (room_count + 1)
        for row in range(1, course_count + 1):
            matched_row[0] = row
            min_cost = [math.inf] * (room_count + 1)
            used = [False] * (room_count + 1)
            column = 0
            while True:
                used[column] = True
                active_row = matched_row[column]
                delta = math.inf
                next_column = 0
                for candidate in range(1, room_count + 1):
                    if used[candidate]:
                        continue
                    reduced = costs[active_row - 1][candidate - 1] - row_potential[active_row] - column_potential[candidate]
                    if reduced < min_cost[candidate]:
                        min_cost[candidate] = reduced
                        previous_column[candidate] = column
                    if min_cost[candidate] < delta:
                        delta = min_cost[candidate]
                        next_column = candidate
                if not math.isfinite(delta):
                    feasible = False
                    break
                for candidate in range(room_count + 1):
                    if used[candidate]:
                        row_potential[matched_row[candidate]] += delta
                        column_potential[candidate] -= delta
                    else:
                        min_cost[candidate] -= delta
                column = next_column
                if matched_row[column] == 0:
                    break
            if not feasible:
                break
            while True:
                previous = previous_column[column]
                matched_row[column] = matched_row[previous]
                column = previous
                if column == 0:
                    break
        assignment = [-1] * course_count
        for column in range(1, room_count + 1):
            if matched_row[column] > 0:
                assignment[matched_row[column] - 1] = column - 1
        choices = tuple(assignment)
    if not feasible or any(index < 0 for index in choices):
        return {"feasible": False, "assignments": [], "reason": "No existe una asignación que cumpla el margen de capacidad."}
    assignments = []
    for course, room_index in zip(courses, choices):
        room = rooms[room_index]
        assignments.append({"course_id": course["course_id"], "room_id": room["room_id"],
                            "attendance": course["attendance"], "capacity": room["capacity"],
                            "utilization_pct": round(course["attendance"] / room["capacity"] * 100, 1),
                            "nominal_power_kw": room["power_kw"]})
    total_power = sum(float(rooms[index]["power_kw"]) for index in choices)
    return {"feasible": True, "assignments": assignments, "total_nominal_power_kw": round(total_power, 3),
            "objective": "minimize_sum_of_nominal_power", "note": "Optimización académica; valida horarios, distancias y accesibilidad antes de aplicar."}
