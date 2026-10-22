from fastapi.testclient import TestClient

from app.main import app


def test_capabilities_endpoint_documents_algorithms_and_operational_limits():
    response = TestClient(app).get("/v1/capabilities")

    assert response.status_code == 200
    body = response.json()
    features = {feature["name"]: feature for feature in body["features"]}
    assert body["service"] == "CampusNexo AI Service"
    assert features["occupancy"]["mode"] == "kalman_escalar_pesos_fijos_no_calibrado"
    assert features["vision"]["mode"] == "optional_yolo"
    assert "no libera puestos automáticamente" in features["library_desk_state"]["summary"]
    assert body["limits"] == {
        "tracked_spaces": 2000,
        "assignment_courses": 18,
        "vision_image_bytes": 8 * 1024 * 1024,
        "thermal_horizon_minutes": 120,
    }
