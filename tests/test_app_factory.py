from fastapi.testclient import TestClient

from app.api.app_factory import create_app
from app.infrastructure.occupancy_registry import OccupancyFilterRegistry
from app.infrastructure.vision import YoloCounter


def test_factory_builds_independent_runtime_state_for_each_application():
    first = create_app()
    second = create_app()

    assert first.state.occupancy_registry is not second.state.occupancy_registry
    assert first.state.vision_counter is not second.state.vision_counter


def test_factory_accepts_injected_runtime_adapters():
    registry = OccupancyFilterRegistry(max_spaces=5)
    counter = YoloCounter()

    application = create_app(registry, counter)

    assert application.state.occupancy_registry is registry
    assert application.state.vision_counter is counter
    assert TestClient(application).get("/health").status_code == 200


def test_readiness_reports_required_runtime_adapters_and_optional_vision():
    application = create_app()

    response = TestClient(application).get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "model weights" in response.json()["optional_features"]["vision"]


def test_readiness_fails_when_a_required_adapter_is_missing():
    application = create_app()
    application.state.occupancy_registry = None

    response = TestClient(application).get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["missing"] == ["occupancy_registry"]


def test_readiness_reports_all_missing_runtime_adapters_in_stable_order():
    application = create_app()
    application.state.occupancy_registry = None
    application.state.vision_counter = None

    response = TestClient(application).get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["missing"] == ["occupancy_registry", "vision_counter"]
