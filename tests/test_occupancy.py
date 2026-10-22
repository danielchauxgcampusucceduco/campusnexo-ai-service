from fastapi.testclient import TestClient

from app.domain.occupancy import KalmanOccupancy, desk_state, internal_confidence
from app.main import app
from eval.evaluate import evaluate


def test_estimate_converges_to_a_steady_room():
    kalman = KalmanOccupancy()
    for _ in range(40):
        estimate, _ = kalman.update(20, 415 + 20 * 14.5, round(20 / 0.88), 415)
    assert abs(estimate - 20) <= 1


def test_without_camera_the_filter_is_less_sure():
    with_camera, without_camera = KalmanOccupancy(), KalmanOccupancy()
    for _ in range(10):
        _, sure = with_camera.update(12, 700, 14)
        _, unsure = without_camera.update(None, 700, 14)
    assert unsure < sure


def test_filter_rejects_invalid_measurements_without_poisoning_its_state():
    import pytest

    kalman = KalmanOccupancy()
    for values in ((None, float("nan"), 2), (None, 500, -1), (1.5, 500, 2)):
        with pytest.raises(ValueError):
            kalman.update(*values)
    assert kalman.estimate == 0.0
    assert kalman.variance == 1.0


def test_filter_rejects_invalid_initial_covariance():
    import pytest

    with pytest.raises(ValueError, match="varianza de medición"):
        KalmanOccupancy(measurement_variance=0)


def test_confidence_is_bounded_and_only_reflects_variance():
    assert internal_confidence(0) == 100.0
    assert internal_confidence(10) == 0.0


def test_confidence_saturates_for_variance_outside_its_reporting_scale():
    assert internal_confidence(5) == 0.0
    assert internal_confidence(100) == 0.0
    assert internal_confidence(-1) == 100.0


def test_desk_rules():
    assert desk_state(1, 3, 2000) == "OCCUPIED_VERIFIED"
    assert desk_state(0, 1, 60) == "POSSIBLE_ABANDONMENT"
    assert desk_state(0, 1, 900) == "RELEASE_RECOMMENDED"
    assert desk_state(0, 0, 0) == "AVAILABLE"


def test_api_says_what_the_estimate_is():
    client = TestClient(app)
    response = client.post("/v1/occupancy/estimate", json={"space_id": "421-A", "yolo_people": 10,
                                                            "co2_ppm": 600, "wifi_devices": 11})
    assert response.status_code == 200
    body = response.json()
    assert body["is_estimate"] is True
    assert body["method"].endswith("no_calibrado")
    assert "no probabilidad" in body["confidence_meaning"]
    assert client.post("/v1/occupancy/estimate", json={"space_id": "421-A", "co2_ppm": -1,
                                                        "wifi_devices": 1}).status_code == 422


def test_vision_without_the_extra_answers_503_not_a_fake_count():
    client = TestClient(app)
    response = client.post("/v1/vision/count", content=b"not-an-image", headers={"Content-Type": "image/jpeg"})
    assert response.status_code in (400, 503)


def test_occupancy_api_rejects_blank_space_id_and_trims_valid_identifiers():
    client = TestClient(app)
    blank = client.post("/v1/occupancy/estimate", json={
        "space_id": "   ", "co2_ppm": 600, "wifi_devices": 5,
    })
    trimmed = client.post("/v1/occupancy/estimate", json={
        "space_id": " A-301 ", "co2_ppm": 600, "wifi_devices": 5,
    })

    assert blank.status_code == 422
    assert trimmed.status_code == 200
    assert trimmed.json()["space_id"] == "A-301"


def test_evaluation_reports_error_metrics_from_the_given_rows():
    rows = [{"space_id": "A", "yolo_people": "5", "co2_ppm": "500", "wifi_devices": "5", "outdoor_co2_ppm": "415",
             "true_people": "5"} for _ in range(10)]
    result = evaluate(rows, tolerance=2)
    assert result["overall"]["n"] == 10
    assert result["with_camera"]["n"] == 10
    assert result["without_camera"]["n"] == 0
    assert result["overall"]["mae"] >= 0
