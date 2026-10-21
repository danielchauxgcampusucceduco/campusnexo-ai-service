"""Asignación óptima exacta por programación dinámica para instancias pequeñas."""
from functools import lru_cache

def assign_rooms(courses: list[dict], rooms: list[dict], safety_margin: float = 1.10) -> dict:
    if len(courses) > 18:
        raise ValueError("La demo exacta admite hasta 18 cursos; use un solver MILP para instancias mayores")
    if not 0 < safety_margin <= 2:
        raise ValueError("safety_margin fuera de rango")
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
