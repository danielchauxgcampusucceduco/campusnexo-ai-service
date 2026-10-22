import re
import logging

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.app_factory import create_app
from app.infrastructure.request_context import request_context


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


def test_middleware_logs_failure_status_when_endpoint_raises(caplog):
    application = FastAPI()
    application.middleware("http")(request_context)

    @application.get("/failure")
    def failure():
        raise RuntimeError("upstream failed")

    caplog.set_level(logging.INFO, logger="campusnexo.http")
    response = TestClient(application, raise_server_exceptions=False).get("/failure")

    assert response.status_code == 500
    record = next(record for record in caplog.records if record.name == "campusnexo.http")
    assert record.http_status == 500
