import csv
from pathlib import Path

import pytest

from app.domain.occupancy import NO_DATA_SIGMA, confidence_pct, fuse_occupancy

GOLDEN = Path(__file__).with_name("fusion_golden_cases.csv")


def golden_cases() -> list[dict]:
    with GOLDEN.open(encoding="utf-8") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


def test_the_same_reference_cases_as_the_java_twin_are_reproduced():
    cases = golden_cases()
    assert len(cases) == 7
    for case in cases:
        # Camera only: the backend no longer receives CO2, so the shared cases carry none (the area does not matter then).
        fusion = fuse_occupancy(int(case["camara"]) if case["camara"] else None, None,
                                int(case["wifi"]) if case["wifi"] else None, 48.0)
        assert fusion.estimate == pytest.approx(float(case["estimacion"]), abs=0.01), case["caso"]
        assert fusion.sigma == pytest.approx(float(case["sigma"]), abs=0.01), case["caso"]
        assert fusion.confidence_pct(int(case["capacidad"])) == pytest.approx(float(case["confianza_pct"]), abs=0.05)


def test_the_camera_dominates_and_without_it_the_estimate_is_less_sure():
    with_camera = fuse_occupancy(26, 780, 30, 48, 420)
    without_camera = fuse_occupancy(None, 780, 30, 48, 420)
    assert with_camera.people() == 26
    assert without_camera.sigma > 5 * with_camera.sigma
    assert sum(source.weight for source in with_camera.sources) == pytest.approx(1, abs=0.001)
    assert with_camera.sources[0].source == "camara_yolo" and with_camera.sources[0].weight > 0.95


def test_co2_evidence_scales_with_the_room_size():
    small = fuse_occupancy(None, 820, 0, 48, 420)
    large = fuse_occupancy(None, 820, 0, 216, 420)
    assert large.sources[0].people == pytest.approx(small.sources[0].people * 4.5, rel=0.001)


def test_the_estimator_has_no_memory_between_calls():
    first = fuse_occupancy(12, 700, 14, 48, 420)
    fuse_occupancy(40, 1500, 60, 48, 420)
    assert fuse_occupancy(12, 700, 14, 48, 420) == first


@pytest.mark.parametrize("values", [
    (None, float("nan"), 2, 48, 420), (None, 500, -1, 48, 420), (1.5, 500, 2, 48, 420), (1001, 500, 2, 48, 420),
    (None, 10001, 2, 48, 420), (None, 500, 2, 0, 420), (None, 500, 2, 48, 1001), (True, 500, 2, 48, 420),
    (None, "500", 2, 48, 420),
])
def test_invalid_measurements_are_rejected(values):
    with pytest.raises(ValueError):
        fuse_occupancy(*values)


def test_confidence_is_the_margin_of_error_relative_to_the_room():
    assert confidence_pct(0, 36) == 100.0
    assert confidence_pct(3.6, 36) == 90.0
    assert confidence_pct(100, 36) == 0.0
    for sigma in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="sigma"):
            confidence_pct(sigma, 36)


def test_without_co2_the_fusion_uses_only_what_arrived():
    camera_only = fuse_occupancy(20, None, None, 48)
    assert [s.source for s in camera_only.sources] == ["camara_yolo"]
    assert camera_only.people() == 20 and camera_only.sigma == pytest.approx(0.8)
    with_wifi = fuse_occupancy(20, None, 25, 48)
    assert [s.source for s in with_wifi.sources] == ["camara_yolo", "wifi_dispositivos"]
    assert with_wifi.sigma < camera_only.sigma
    wifi_only = fuse_occupancy(None, None, 25, 48)
    assert [s.source for s in wifi_only.sources] == ["wifi_dispositivos"] and wifi_only.people() == 20


def test_without_any_measurement_the_answer_is_unknown_not_empty():
    fusion = fuse_occupancy(None, None, None, 48)
    assert fusion.sources == () and fusion.people() == 0
    assert fusion.sigma == NO_DATA_SIGMA
    assert fusion.confidence_pct(5000) == 0.0 and fusion.confidence_pct(36) == 0.0
