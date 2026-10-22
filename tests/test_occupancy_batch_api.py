from fastapi.testclient import TestClient

from app.api.app_factory import create_app
from app.infrastructure.occupancy_registry import OccupancyFilterRegistry


def reading(space_id: str, people: int) -> dict:
    return {
        "space_id": space_id,
        "yolo_people": people,
        "co2_ppm": 600,
        "wifi_devices": 8,
    }


def test_batch_preserves_order_and_keeps_filter_state_isolated_by_space():
    client = TestClient(create_app(occupancy_registry=OccupancyFilterRegistry()))

    response = client.post("/v1/occupancy/estimate/batch", json={
        "measurements": [reading("A-301", 8), reading("B-201", 20)],
    })
    isolated_client = TestClient(create_app(occupancy_registry=OccupancyFilterRegistry()))
    isolated = isolated_client.post("/v1/occupancy/estimate/batch", json={
        "measurements": [reading("A-301", 8)],
    })

    assert response.status_code == 200
    estimates = response.json()["estimates"]
    assert [item["space_id"] for item in estimates] == ["A-301", "B-201"]
    assert estimates[0]["occupancy_estimate"] < estimates[1]["occupancy_estimate"]
    assert isolated.json()["estimates"][0]["occupancy_estimate"] == estimates[0]["occupancy_estimate"]
    assert all(item["is_estimate"] is True for item in estimates)


def test_batch_rejects_duplicate_space_ids_with_standard_validation_response():
    client = TestClient(create_app(occupancy_registry=OccupancyFilterRegistry()))

    response = client.post("/v1/occupancy/estimate/batch", json={
        "measurements": [reading("A-301", 8), reading("A-301", 9)],
    })

    assert response.status_code == 422
