from fastapi.testclient import TestClient
import pytest

from app.api.app_factory import create_app
from app.infrastructure.vision import YoloCounter


def test_factory_builds_independent_runtime_state_for_each_application():
    first = create_app(api_key="")
    second = create_app(api_key="")

    assert first.state.vision_counter is not second.state.vision_counter


def test_factory_accepts_an_injected_vision_adapter():
    counter = YoloCounter()

    application = create_app(counter, api_key="")

    assert application.state.vision_counter is counter
    assert TestClient(application).get("/health").status_code == 200


def test_factory_reads_the_service_key_from_the_environment(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "clave-desde-el-entorno-de-24")

    application = create_app()

    assert application.state.api_key == "clave-desde-el-entorno-de-24"
    assert TestClient(application).post("/v1/occupancy/estimate", json={}).status_code == 401


def test_readiness_reports_required_runtime_adapters_and_optional_vision():
    response = TestClient(create_app(api_key="")).get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "model weights" in response.json()["optional_features"]["vision"]


def test_readiness_fails_when_a_required_adapter_is_missing():
    application = create_app(api_key="")
    application.state.vision_counter = None

    response = TestClient(application).get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["missing"] == ["vision_counter"]


@pytest.mark.parametrize("key", ["", None])
def test_without_a_key_the_service_is_open_for_local_development(monkeypatch, key):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    application = create_app(api_key=key)

    assert application.state.api_key == ""
