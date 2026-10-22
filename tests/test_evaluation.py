import json
import pytest

from eval.evaluate import evaluate, main


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


def test_cli_reports_invalid_tolerance_as_argument_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["evaluate.py", "conteos.csv", "--tolerance", "-1"])

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert "debe ser un número finito no negativo" in capsys.readouterr().err


def test_cli_writes_the_same_per_space_report_to_stdout_and_json(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "conteos.csv"
    output_path = tmp_path / "resultado.json"
    input_path.write_text(
        "space_id,co2_ppm,wifi_devices,true_people,yolo_people\nA-301,500,4,5,5\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate.py", str(input_path), "--json", str(output_path)],
    )

    main()

    printed = json.loads(capsys.readouterr().out)
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert printed == saved
    assert printed["per_space"]["A-301"]["n"] == 1


def test_cli_reports_invalid_csv_rows_without_a_traceback(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "conteos.csv"
    input_path.write_text(
        "space_id,co2_ppm,wifi_devices,true_people\nA-301,nan,4,5\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["evaluate.py", str(input_path)])

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert "fila 2: co2_ppm" in capsys.readouterr().err
