from fastapi.testclient import TestClient
import pytest

from app.api.app_factory import create_app

KEY = "clave-de-pruebas-de-24-caracteres"


def reading(**overrides) -> dict:
    body = {"space_id": "421-A", "yolo_people": 10, "co2_ppm": 600, "wifi_devices": 11, "area_sqm": 48,
            "capacity": 36}
    body.update(overrides)
    return body


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(api_key=""))


def test_api_says_what_the_estimate_is_and_how_each_source_weighed(client):
    response = client.post("/v1/occupancy/estimate", json=reading())
    assert response.status_code == 200
    body = response.json()
    assert body["is_estimate"] is True
    assert body["method"] == "fusion_varianza_inversa_no_calibrada"
    assert "no probabilidad" in body["confidence_meaning"]
    assert [source["source"] for source in body["sources"]] == ["camara_yolo", "co2_balance_masico",
                                                               "wifi_dispositivos"]
    assert body["sigma_people"] > 0
    assert client.post("/v1/occupancy/estimate", json=reading(co2_ppm=-1)).status_code == 422


def test_a_retried_request_gets_exactly_the_same_answer(client):
    first = client.post("/v1/occupancy/estimate", json=reading()).json()
    second = client.post("/v1/occupancy/estimate", json=reading()).json()
    assert first == second


def test_area_and_capacity_are_required_because_the_model_needs_them(client):
    body = reading()
    del body["area_sqm"]
    assert client.post("/v1/occupancy/estimate", json=body).status_code == 422
    assert client.post("/v1/occupancy/estimate", json=reading(capacity=0)).status_code == 422


def test_the_service_key_protects_every_route_but_health():
    protected = TestClient(create_app(api_key=KEY))
    assert protected.get("/health").status_code == 200
    assert protected.post("/v1/occupancy/estimate", json=reading()).status_code == 401
    assert protected.post("/v1/occupancy/estimate", json=reading(),
                          headers={"X-API-Key": "otra-clave-cualquiera-de-24"}).status_code == 401
    assert protected.post("/v1/occupancy/estimate", json=reading(), headers={"X-API-Key": KEY}).status_code == 200
    assert protected.get("/v1/capabilities").status_code == 200


def test_a_short_service_key_is_refused_at_startup():
    with pytest.raises(ValueError, match="24 caracteres"):
        create_app(api_key="corta")


def test_vision_without_the_extra_answers_503_not_a_fake_count(client):
    response = client.post("/v1/vision/count", content=b"not-an-image", headers={"Content-Type": "image/jpeg"})
    assert response.status_code in (400, 503)


def test_occupancy_api_rejects_blank_space_id_and_trims_valid_identifiers(client):
    assert client.post("/v1/occupancy/estimate", json=reading(space_id="   ")).status_code == 422
    trimmed = client.post("/v1/occupancy/estimate", json=reading(space_id=" A-301 "))
    assert trimmed.status_code == 200
    assert trimmed.json()["space_id"] == "A-301"


@pytest.mark.parametrize("field, value", [("yolo_people", True), ("co2_ppm", True), ("capacity", "36")])
def test_occupancy_api_rejects_values_of_the_wrong_type(client, field, value):
    assert client.post("/v1/occupancy/estimate", json=reading(**{field: value})).status_code == 422
