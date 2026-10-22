import pytest

from eval.evaluate import evaluate


def test_evaluation_reports_error_metrics_by_space_in_stable_key_order():
    result = evaluate(
        [
            {
                "space_id": "B-201",
                "co2_ppm": "500",
                "wifi_devices": "3",
                "true_people": "4",
                "yolo_people": "4",
            },
            {
                "space_id": "A-301",
                "co2_ppm": "600",
                "wifi_devices": "5",
                "true_people": "6",
                "yolo_people": "6",
            },
            {
                "space_id": "A-301",
                "co2_ppm": "610",
                "wifi_devices": "5",
                "true_people": "6",
                "yolo_people": "6",
            },
        ],
        tolerance=1,
    )

    assert result["overall"]["n"] == 3
    assert list(result["per_space"]) == ["A-301", "B-201"]
    assert result["per_space"]["A-301"]["n"] == 2
    assert result["per_space"]["B-201"]["n"] == 1


@pytest.mark.parametrize("tolerance", [-1, float("nan"), float("inf")])
def test_evaluation_rejects_invalid_error_tolerances(tolerance):
    with pytest.raises(ValueError, match="tolerance debe ser"):
        evaluate([], tolerance=tolerance)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("space_id", "  "),
        ("co2_ppm", "nan"),
        ("wifi_devices", "2.5"),
        ("true_people", "-1"),
        ("yolo_people", "1001"),
        ("outdoor_co2_ppm", "1200"),
    ],
)
def test_evaluation_rejects_invalid_measurement_rows(column, value):
    row = {
        "space_id": "A-301",
        "co2_ppm": "500",
        "wifi_devices": "4",
        "true_people": "5",
    }
    row[column] = value

    with pytest.raises(ValueError, match="fila 2"):
        evaluate([row], tolerance=1)
