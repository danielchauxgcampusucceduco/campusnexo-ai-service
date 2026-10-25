from fastapi.testclient import TestClient

from app.api.app_factory import create_app
from app.settings import MAX_OCCUPANCY_BATCH_ITEMS


def reading(space_id: str, people: int) -> dict:
    return {"space_id": space_id, "yolo_people": people, "co2_ppm": 600, "wifi_devices": 8, "area_sqm": 48,
            "capacity": 36}


def client() -> TestClient:
    return TestClient(create_app(api_key=""))


def test_batch_preserves_order_and_answers_each_reading_like_a_single_estimate():
    service = client()

    response = service.post("/v1/occupancy/estimate/batch", json={
        "measurements": [reading("A-301", 8), reading("B-201", 20)],
    })
    single = service.post("/v1/occupancy/estimate", json=reading("A-301", 8))

    assert response.status_code == 200
    estimates = response.json()["estimates"]
    assert [item["space_id"] for item in estimates] == ["A-301", "B-201"]
    assert estimates[0]["occupancy_estimate"] < estimates[1]["occupancy_estimate"]
    assert estimates[0] == single.json()
    assert all(item["is_estimate"] is True for item in estimates)


def test_batch_rejects_duplicate_space_ids_with_standard_validation_response():
    response = client().post("/v1/occupancy/estimate/batch", json={
        "measurements": [reading("A-301", 8), reading("A-301", 9)],
    })

    assert response.status_code == 422


def test_batch_rejects_space_ids_that_collide_after_trimming():
    response = client().post("/v1/occupancy/estimate/batch", json={
        "measurements": [reading("A-301", 8), reading(" A-301 ", 9)],
    })

    assert response.status_code == 422


def test_batch_rejects_more_readings_than_the_published_limit():
    over_limit = [reading(f"R-{index}", 10) for index in range(MAX_OCCUPANCY_BATCH_ITEMS + 1)]

    response = client().post("/v1/occupancy/estimate/batch", json={"measurements": over_limit})

    assert response.status_code == 422
