from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_assignment_endpoint_returns_a_validated_room_plan():
    response = client.post(
        "/v1/rooms/assignment",
        json={
            "courses": [{"course_id": "IS-101", "attendance": 20}],
            "rooms": [{"room_id": "A-301", "capacity": 24, "power_kw": 1.8}],
            "safety_margin": 1.1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["feasible"] is True
    assert body["assignments"][0]["room_id"] == "A-301"


def test_assignment_endpoint_rejects_invalid_course_and_room_fields():
    response = client.post(
        "/v1/rooms/assignment",
        json={
            "courses": [{"course_id": "", "attendance": -1}],
            "rooms": [{"room_id": "A-301", "capacity": -2, "power_kw": -0.5}],
        },
    )

    assert response.status_code == 422


def test_assignment_endpoint_enforces_the_documented_exact_solver_limit():
    response = client.post(
        "/v1/rooms/assignment",
        json={
            "courses": [{"course_id": str(index), "attendance": 1} for index in range(19)],
            "rooms": [],
        },
    )

    assert response.status_code == 422
