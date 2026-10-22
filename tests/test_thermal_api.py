from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_thermal_endpoint_returns_a_bounded_recommendation():
    response = client.post(
        "/v1/thermal/recommendation",
        json={
            "current_temp_c": 22,
            "outside_temp_c": 14,
            "occupancy": 18,
            "lighting_kw": 1.4,
            "horizon_min": 12,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "1R1C_exact_exponential"
    assert 0 <= body["safe_off_duration_min"] <= 12
    assert "no controla equipos" in body["note"]


def test_thermal_endpoint_rejects_inputs_outside_the_http_contract():
    response = client.post(
        "/v1/thermal/recommendation",
        json={
            "current_temp_c": 22,
            "outside_temp_c": 14,
            "occupancy": -1,
            "lighting_kw": 1.4,
        },
    )

    assert response.status_code == 422
