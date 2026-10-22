import sys
from types import SimpleNamespace

import pytest

from app.infrastructure.vision import YoloCounter


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeModel:
    def __init__(self, boxes):
        self.boxes = boxes
        self.source = None

    def predict(self, *, source, verbose):
        assert verbose is False
        self.source = source
        return [SimpleNamespace(boxes=self.boxes)]


def install_image_decoder(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "cv2",
        SimpleNamespace(IMREAD_COLOR=1, imdecode=lambda _data, _mode: "decoded-frame"),
    )
    monkeypatch.setitem(
        sys.modules,
        "numpy",
        SimpleNamespace(uint8="uint8", frombuffer=lambda raw, dtype: (raw, dtype)),
    )


def test_yolo_adapter_counts_only_person_class_and_returns_no_frame_data(monkeypatch):
    install_image_decoder(monkeypatch)
    model = FakeModel(SimpleNamespace(cls=FakeTensor([0, 1, 0])))
    counter = YoloCounter()
    counter.model = model

    result = counter.count_people(b"jpeg-bytes")

    assert result == {
        "people_count": 2,
        "privacy": "frame_discarded_in_process",
        "model": "yolo26n.pt",
    }
    assert model.source == "decoded-frame"


def test_yolo_adapter_returns_zero_when_the_detector_has_no_boxes(monkeypatch):
    install_image_decoder(monkeypatch)
    counter = YoloCounter()
    counter.model = FakeModel(None)

    assert counter.count_people(b"jpeg-bytes")["people_count"] == 0


def test_yolo_adapter_rejects_an_undecodable_frame(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "cv2",
        SimpleNamespace(IMREAD_COLOR=1, imdecode=lambda _data, _mode: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "numpy",
        SimpleNamespace(uint8="uint8", frombuffer=lambda raw, dtype: (raw, dtype)),
    )

    with pytest.raises(ValueError, match="No se pudo decodificar la imagen"):
        YoloCounter().count_people(b"not-an-image")
