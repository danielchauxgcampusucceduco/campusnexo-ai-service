import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("people=1&objects=2&unattended_seconds=1800", "OCCUPIED_VERIFIED"),
        ("people=0&objects=1&unattended_seconds=899", "POSSIBLE_ABANDONMENT"),
        ("people=0&objects=1&unattended_seconds=900", "RELEASE_RECOMMENDED"),
        ("people=0&objects=0&unattended_seconds=0", "AVAILABLE"),
    ],
)
def test_library_route_exposes_each_desk_state_without_actuating(query, expected):
    response = client.get(f"/v1/library/desk-state?{query}")

    assert response.status_code == 200
    assert response.json()["state"] == expected
    assert response.json()["is_automatic_release"] is False


def test_library_route_rejects_negative_query_values():
    response = client.get("/v1/library/desk-state?people=-1")

    assert response.status_code == 422
