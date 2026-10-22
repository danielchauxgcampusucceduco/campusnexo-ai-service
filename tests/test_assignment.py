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


def test_assignment_finds_global_match_when_the_cheapest_room_is_needed_by_another_course():
    result = assign_rooms(
        [{"course_id": "large", "attendance": 20}, {"course_id": "small", "attendance": 10}],
        [
            {"room_id": "small-room", "capacity": 10, "power_kw": 1},
            {"room_id": "large-room", "capacity": 20, "power_kw": 2},
        ],
        safety_margin=1,
    )

    assert {row["course_id"]: row["room_id"] for row in result["assignments"]} == {
        "large": "large-room", "small": "small-room",
    }
    assert result["total_nominal_power_kw"] == 3


def test_assignment_scales_to_many_rooms_without_enumerating_room_subsets():
    courses = [{"course_id": f"C{i}", "attendance": 10} for i in range(18)]
    rooms = [{"room_id": f"R{i}", "capacity": 10, "power_kw": float(i + 1)} for i in range(200)]

    result = assign_rooms(courses, rooms, safety_margin=1)

    assert result["feasible"] is True
    assert len({row["room_id"] for row in result["assignments"]}) == 18
    assert result["total_nominal_power_kw"] == sum(range(1, 19))


def test_assignment_reports_infeasible_capacity_and_room_count():
    course = [{"course_id": "A", "attendance": 20}]

    no_rooms = assign_rooms(course, [], 1.0)
    too_small = assign_rooms(course, [{"room_id": "R", "capacity": 10, "power_kw": 1}], 1.0)

    assert no_rooms["feasible"] is False
    assert too_small["feasible"] is False
    assert no_rooms["assignments"] == too_small["assignments"] == []


def test_equal_power_solutions_keep_the_input_room_order_deterministically():
    courses = [{"course_id": "A", "attendance": 10}]
    rooms = [
        {"room_id": "R-SECOND", "capacity": 12, "power_kw": 1.0},
        {"room_id": "R-FIRST", "capacity": 12, "power_kw": 1.0},
    ]

    result = assign_rooms(courses, rooms, safety_margin=1.0)

    assert result["assignments"][0]["room_id"] == "R-SECOND"
    assert courses == [{"course_id": "A", "attendance": 10}]
    assert rooms[0]["room_id"] == "R-SECOND"


def test_empty_course_set_is_a_feasible_zero_power_plan():
    result = assign_rooms([], [{"room_id": "A-301", "capacity": 24, "power_kw": 1.8}])

    assert result["feasible"] is True
    assert result["assignments"] == []
    assert result["total_nominal_power_kw"] == 0.0


@pytest.mark.parametrize("course_count", [19])
def test_assignment_rejects_instances_above_exact_solver_limit(course_count):
    courses = [{"course_id": str(i), "attendance": 1} for i in range(course_count)]

    with pytest.raises(ValueError, match="hasta 18 cursos"):
        assign_rooms(courses, [], 1.0)


@pytest.mark.parametrize("margin", [0, -0.1, 2.01])
def test_assignment_rejects_invalid_safety_margin(margin):
    with pytest.raises(ValueError, match="fuera de rango"):
        assign_rooms([], [], margin)


@pytest.mark.parametrize(
    ("courses", "rooms", "message"),
    [
        ([{"course_id": "A", "attendance": -1}], [], "attendance"),
        ([{"course_id": "A", "attendance": True}], [], "attendance"),
        ([], [{"room_id": "R", "capacity": 0, "power_kw": 1}], "capacity"),
        ([], [{"room_id": "R", "capacity": 10, "power_kw": float("inf")}], "power_kw"),
        ([{"course_id": "A", "attendance": 1}, {"course_id": "A", "attendance": 2}], [], "course_id"),
    ],
)
def test_assignment_rejects_invalid_domain_records(courses, rooms, message):
    with pytest.raises(ValueError, match=message):
        assign_rooms(courses, rooms)
