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
