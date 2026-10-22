from fastapi.testclient import TestClient

from app.main import app
from app.settings import (
    MAX_ASSIGNMENT_COURSES,
    MAX_THERMAL_HORIZON_MINUTES,
    MAX_TRACKED_SPACES,
    MAX_VISION_IMAGE_BYTES,
)


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
        "tracked_spaces": MAX_TRACKED_SPACES,
        "assignment_courses": MAX_ASSIGNMENT_COURSES,
        "vision_image_bytes": MAX_VISION_IMAGE_BYTES,
        "thermal_horizon_minutes": MAX_THERMAL_HORIZON_MINUTES,
    }
