from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_vision_route_rejects_unsupported_media_types():
    response = client.post(
        "/v1/vision/count",
        content=b"not an image",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 415


def test_vision_route_rejects_oversized_content_length_before_reading():
    response = client.post(
        "/v1/vision/count",
        content=b"",
        headers={"Content-Type": "image/jpeg", "Content-Length": str(8 * 1024 * 1024 + 1)},
    )

    assert response.status_code == 413


def test_vision_route_maps_decode_failure_to_bad_request(monkeypatch):
    def reject_image(_raw):
        raise ValueError("No se pudo decodificar la imagen")

    monkeypatch.setattr("app.api.routes.vision.vision.count_people", reject_image)
    response = client.post(
        "/v1/vision/count",
        content=b"invalid",
        headers={"Content-Type": "image/png"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No se pudo decodificar la imagen"


def test_vision_route_returns_count_metadata_without_echoing_image(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.vision.vision.count_people",
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
