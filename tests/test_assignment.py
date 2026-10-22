import pytest

from app.domain.assignment import assign_rooms


def test_assignment_minimizes_power_while_meeting_capacity_margin():
    courses = [{"course_id": "A", "attendance": 20}, {"course_id": "B", "attendance": 10}]
    rooms = [
        {"room_id": "large", "capacity": 30, "power_kw": 3.0},
        {"room_id": "small", "capacity": 22, "power_kw": 1.0},
        {"room_id": "medium", "capacity": 15, "power_kw": 1.5},
    ]

    result = assign_rooms(courses, rooms, safety_margin=1.0)

    assert result["feasible"] is True
    assert {item["course_id"]: item["room_id"] for item in result["assignments"]} == {
        "A": "small",
        "B": "medium",
    }
    assert result["total_nominal_power_kw"] == 2.5


def test_assignment_reports_infeasible_capacity_and_room_count():
    course = [{"course_id": "A", "attendance": 20}]

    no_rooms = assign_rooms(course, [], 1.0)
    too_small = assign_rooms(course, [{"room_id": "R", "capacity": 10, "power_kw": 1}], 1.0)

    assert no_rooms["feasible"] is False
    assert too_small["feasible"] is False
    assert no_rooms["assignments"] == too_small["assignments"] == []


@pytest.mark.parametrize("course_count", [19])
def test_assignment_rejects_instances_above_exact_solver_limit(course_count):
    courses = [{"course_id": str(i), "attendance": 1} for i in range(course_count)]

    with pytest.raises(ValueError, match="hasta 18 cursos"):
        assign_rooms(courses, [], 1.0)


@pytest.mark.parametrize("margin", [0, -0.1, 2.01])
def test_assignment_rejects_invalid_safety_margin(margin):
    with pytest.raises(ValueError, match="fuera de rango"):
        assign_rooms([], [], margin)
