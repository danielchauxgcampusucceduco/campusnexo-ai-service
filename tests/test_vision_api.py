from fastapi.testclient import TestClient
from threading import get_ident

from app.main import app
from app.infrastructure.vision import VisionUnavailable


client = TestClient(app)


def test_vision_route_rejects_unsupported_media_types():
    response = client.post(
        "/v1/vision/count",
        content=b"not an image",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 415


def test_vision_route_rejects_empty_body_without_loading_the_model(monkeypatch):
    def should_not_run(_raw):
        raise AssertionError("el adaptador no debe ejecutarse con una imagen vacía")

    monkeypatch.setattr(app.state.vision_counter, "count_people", should_not_run)
    response = client.post("/v1/vision/count", content=b"", headers={"Content-Type": "image/jpeg"})

    assert response.status_code == 400
    assert response.json()["detail"] == "La imagen no puede estar vacía"


def test_vision_route_rejects_oversized_content_length_before_reading():
    response = client.post(
        "/v1/vision/count",
        content=b"",
        headers={"Content-Type": "image/jpeg", "Content-Length": str(8 * 1024 * 1024 + 1)},
    )

    assert response.status_code == 413


def test_vision_route_enforces_stream_limit_when_content_length_understates_body():
    response = client.post(
        "/v1/vision/count",
        content=b"x" * (8 * 1024 * 1024 + 1),
        headers={"Content-Type": "image/jpeg", "Content-Length": "1"},
    )

    assert response.status_code == 413


def test_vision_route_maps_decode_failure_to_bad_request(monkeypatch):
    def reject_image(_raw):
        raise ValueError("No se pudo decodificar la imagen")

    monkeypatch.setattr(app.state.vision_counter, "count_people", reject_image)
    response = client.post(
        "/v1/vision/count",
        content=b"invalid",
        headers={"Content-Type": "image/png"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No se pudo decodificar la imagen"


def test_vision_route_maps_unavailable_model_to_service_unavailable(monkeypatch):
    def unavailable(_raw):
        raise VisionUnavailable("YOLO no disponible")

    monkeypatch.setattr(app.state.vision_counter, "count_people", unavailable)
    response = client.post(
        "/v1/vision/count", content=b"image", headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "YOLO no disponible"


def test_vision_route_returns_count_metadata_without_echoing_image(monkeypatch):
    monkeypatch.setattr(
        app.state.vision_counter,
        "count_people",
        lambda _raw: {"people_count": 3, "privacy": "frame_discarded_in_process", "model": "demo.pt"},
    )
    response = client.post(
        "/v1/vision/count",
        content=b"image bytes",
        headers={"Content-Type": "image/webp"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "people_count": 3,
        "privacy": "frame_discarded_in_process",
        "model": "demo.pt",
    }


def test_vision_route_runs_blocking_model_inference_off_the_event_loop(monkeypatch):
    caller_thread = get_ident()
    inference_threads = []
    monkeypatch.setattr(
        app.state.vision_counter,
        "count_people",
        lambda _raw: inference_threads.append(get_ident()) or {
            "people_count": 0, "privacy": "frame_discarded_in_process", "model": "demo.pt",
        },
    )

    response = client.post("/v1/vision/count", content=b"image", headers={"Content-Type": "image/jpeg"})

    assert response.status_code == 200
    assert inference_threads and inference_threads[0] != caller_thread
