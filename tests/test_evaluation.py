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
