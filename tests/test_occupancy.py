import csv
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.api.app_factory import create_app
from app.domain.occupancy import confidence_pct, desk_state, fuse_occupancy
from eval.evaluate import evaluate

GOLDEN = Path(__file__).with_name("fusion_golden_cases.csv")
KEY = "clave-de-pruebas-de-24-caracteres"


def reading(**overrides) -> dict:
    body = {"space_id": "421-A", "yolo_people": 10, "co2_ppm": 600, "wifi_devices": 11, "area_sqm": 48,
            "capacity": 36}
    body.update(overrides)
    return body


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(api_key=""))


def golden_cases() -> list[dict]:
    with GOLDEN.open(encoding="utf-8") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


def test_the_same_reference_cases_as_the_java_twin_are_reproduced():
    cases = golden_cases()
    assert len(cases) == 6
    for case in cases:
        fusion = fuse_occupancy(int(case["camara"]) if case["camara"] else None, float(case["co2_ppm"]),
                                int(case["wifi"]), float(case["area_m2"]), float(case["co2_exterior_ppm"]))
        assert fusion.estimate == pytest.approx(float(case["estimacion"]), abs=0.01), case["caso"]
        assert fusion.sigma == pytest.approx(float(case["sigma"]), abs=0.01), case["caso"]
        assert fusion.confidence_pct(int(case["capacidad"])) == pytest.approx(float(case["confianza_pct"]), abs=0.05)


def test_the_camera_dominates_and_without_it_the_estimate_is_less_sure():
    with_camera = fuse_occupancy(26, 780, 30, 48, 420)
    without_camera = fuse_occupancy(None, 780, 30, 48, 420)
    assert with_camera.people() == 26
    assert without_camera.sigma > 5 * with_camera.sigma
    assert sum(source.weight for source in with_camera.sources) == pytest.approx(1, abs=0.001)
    assert with_camera.sources[0].source == "camara_yolo" and with_camera.sources[0].weight > 0.95


def test_co2_evidence_scales_with_the_room_size():
    small = fuse_occupancy(None, 820, 0, 48, 420)
    large = fuse_occupancy(None, 820, 0, 216, 420)
    assert large.sources[0].people == pytest.approx(small.sources[0].people * 4.5, rel=0.001)


def test_the_estimator_has_no_memory_between_calls():
    first = fuse_occupancy(12, 700, 14, 48, 420)
    fuse_occupancy(40, 1500, 60, 48, 420)
    assert fuse_occupancy(12, 700, 14, 48, 420) == first


@pytest.mark.parametrize("values", [
    (None, float("nan"), 2, 48, 420), (None, 500, -1, 48, 420), (1.5, 500, 2, 48, 420), (1001, 500, 2, 48, 420),
    (None, 10001, 2, 48, 420), (None, 500, 2, 0, 420), (None, 500, 2, 48, 1001), (True, 500, 2, 48, 420),
    (None, "500", 2, 48, 420),
])
def test_invalid_measurements_are_rejected(values):
    with pytest.raises(ValueError):
        fuse_occupancy(*values)


def test_confidence_is_the_margin_of_error_relative_to_the_room():
    assert confidence_pct(0, 36) == 100.0
    assert confidence_pct(3.6, 36) == 90.0
    assert confidence_pct(100, 36) == 0.0
    for sigma in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="sigma"):
            confidence_pct(sigma, 36)


def test_desk_rules():
    assert desk_state(1, 3, 2000) == "OCCUPIED_VERIFIED"
    assert desk_state(0, 1, 60) == "POSSIBLE_ABANDONMENT"
    assert desk_state(0, 1, 900) == "RELEASE_RECOMMENDED"
    assert desk_state(0, 0, 0) == "AVAILABLE"


def test_desk_domain_rejects_negative_and_boolean_counts():
    for values in ((-1, 0, 0), (0, True, 0), (0, 1, -1), (0, 1, 0, 0)):
        with pytest.raises(ValueError):
            desk_state(*values)


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


def test_evaluation_reports_error_metrics_from_the_given_rows():
    rows = [{"space_id": "A", "yolo_people": "5", "co2_ppm": "500", "wifi_devices": "5", "outdoor_co2_ppm": "415",
             "area_sqm": "48", "capacity": "36", "true_people": "5"} for _ in range(10)]
    result = evaluate(rows, tolerance=2)
    assert result["overall"]["n"] == 10
    assert result["with_camera"]["n"] == 10
    assert result["without_camera"]["n"] == 0
    assert result["overall"]["mae"] == 0
