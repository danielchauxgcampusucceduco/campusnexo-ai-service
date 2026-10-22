from fastapi.testclient import TestClient

from app.main import app
from app.settings import (
    MAX_ASSIGNMENT_COURSES,
    MAX_ASSIGNMENT_ROOMS,
    MAX_ASSIGNMENT_ATTENDANCE,
    MAX_DESK_COUNT,
    MAX_OCCUPANCY_BATCH_ITEMS,
    MAX_ROOM_CAPACITY,
    MAX_ROOM_POWER_KW,
    MAX_THERMAL_HORIZON_MINUTES,
    MAX_UNATTENDED_SECONDS,
    MAX_VISION_IMAGE_BYTES,
)


def test_capabilities_endpoint_documents_algorithms_and_operational_limits():
    response = TestClient(app).get("/v1/capabilities")

    assert response.status_code == 200
    body = response.json()
    features = {feature["name"]: feature for feature in body["features"]}
    assert body["service"] == "CampusNexo AI Service"
    assert features["occupancy"]["mode"] == "fusion_varianza_inversa_no_calibrada"
    assert features["occupancy_batch"]["mode"] == "stateless_fusion_per_reading"
    assert features["thermal"]["mode"] == "1R1C_exact_exponential"
    assert features["vision"]["mode"] == "optional_yolo"
    assert "no libera puestos automáticamente" in features["library_desk_state"]["summary"]
    assert body["limits"] == {
        "occupancy_batch_items": MAX_OCCUPANCY_BATCH_ITEMS,
        "assignment_courses": MAX_ASSIGNMENT_COURSES,
        "assignment_rooms": MAX_ASSIGNMENT_ROOMS,
        "course_attendance": MAX_ASSIGNMENT_ATTENDANCE,
        "room_capacity": MAX_ROOM_CAPACITY,
        "room_power_kw": MAX_ROOM_POWER_KW,
        "vision_image_bytes": MAX_VISION_IMAGE_BYTES,
        "thermal_horizon_minutes": MAX_THERMAL_HORIZON_MINUTES,
        "desk_count": MAX_DESK_COUNT,
        "unattended_seconds": MAX_UNATTENDED_SECONDS,
    }
