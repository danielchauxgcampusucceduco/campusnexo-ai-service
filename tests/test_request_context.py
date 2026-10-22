import re
import logging

from fastapi.testclient import TestClient

from app.api.app_factory import create_app


def test_middleware_echoes_a_sanitized_request_id_and_logs_request_metadata(caplog):
    application = create_app()
    client = TestClient(application)
    caplog.set_level(logging.INFO, logger="campusnexo.http")

    response = client.get("/health", headers={"X-Request-ID": "defense.run-42"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "defense.run-42"
    record = next(record for record in caplog.records if record.name == "campusnexo.http")
    assert record.request_id == "defense.run-42"
    assert record.http_method == "GET"
    assert record.http_path == "/health"
    assert record.http_status == 200
    assert record.duration_ms >= 0


def test_middleware_replaces_an_invalid_request_id():
    response = TestClient(create_app()).get("/health", headers={"X-Request-ID": "bad id"})

    assert re.fullmatch(r"[a-f0-9]{32}", response.headers["X-Request-ID"])
