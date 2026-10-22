#!/usr/bin/env python3
"""Mide el estimador de ocupación contra conteos reales.

Entrada: un CSV con una fila por lectura, en orden de tiempo dentro de cada espacio (ver
``plantilla_conteos.csv``). ``true_people`` es el conteo de referencia hecho por una persona (sin
identificar a nadie). ``yolo_people`` puede ir vacío si la cámara no estaba disponible.

Salida (en pantalla y opcionalmente en JSON):

* n, MAE, RMSE y sesgo (media de estimado − real), global y con/sin cámara;
* tabla de calibración: para cada rango de ``confidence_pct``, la fracción de lecturas cuyo error
  absoluto está dentro de la tolerancia. Si ``confidence_pct`` fuese una probabilidad calibrada, esa
  fracción subiría con la confianza; si no sube, no debe presentarse como probabilidad.

Uso:  python eval/evaluate.py conteos.csv --tolerance 2 --json resultados.json

No incluye datos: los números que reporte son los de *tu* CSV. No publiques resultados sin el CSV,
el protocolo de conteo y la versión del servicio con que se midieron.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain.occupancy import KalmanOccupancy  # noqa: E402

REQUIRED = ("space_id", "co2_ppm", "wifi_devices", "true_people")
BINS = ((0, 50), (50, 70), (70, 85), (85, 101))


def metrics(errors: list[float]) -> dict:
    if not errors:
        return {"n": 0}
    n = len(errors)
    return {"n": n, "mae": round(sum(abs(e) for e in errors) / n, 3),
            "rmse": round(math.sqrt(sum(e * e for e in errors) / n), 3), "bias": round(sum(errors) / n, 3)}


def evaluate(rows: list[dict], tolerance: float) -> dict:
    filters: dict[str, KalmanOccupancy] = defaultdict(KalmanOccupancy)
    per_space_errors: dict[str, list[float]] = defaultdict(list)
    all_errors, with_camera, without_camera = [], [], []
    calibration = {bin_: [0, 0] for bin_ in BINS}
    for line, row in enumerate(rows, start=2):
        missing = [column for column in REQUIRED if row.get(column, "") == ""]
        if missing:
            raise ValueError(f"fila {line}: faltan {', '.join(missing)}")
        yolo = row.get("yolo_people", "")
        yolo_people = int(yolo) if yolo != "" else None
        outdoor = float(row["outdoor_co2_ppm"]) if row.get("outdoor_co2_ppm") else 415.0
        estimate, confidence = filters[row["space_id"]].update(yolo_people, float(row["co2_ppm"]),
                                                               int(row["wifi_devices"]), outdoor)
        error = estimate - float(row["true_people"])
        all_errors.append(error)
        per_space_errors[row["space_id"]].append(error)
        (with_camera if yolo_people is not None else without_camera).append(error)
        for low, high in BINS:
            if low <= confidence < high:
                calibration[(low, high)][0] += 1
                calibration[(low, high)][1] += abs(error) <= tolerance
    return {
        "overall": metrics(all_errors),
        "per_space": {space_id: metrics(errors) for space_id, errors in sorted(per_space_errors.items())},
        "with_camera": metrics(with_camera),
        "without_camera": metrics(without_camera),
        "tolerance_people": tolerance,
        "calibration": [{"confidence_pct": f"{low}-{min(high, 100)}", "n": total,
                         "within_tolerance": round(hits / total, 3) if total else None}
                        for (low, high), (total, hits) in calibration.items()],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--tolerance", type=float, default=2.0, help="personas de error aceptadas")
    parser.add_argument("--json", type=Path, help="guardar el resultado en este archivo")
    args = parser.parse_args()
    with args.csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        sys.exit("El CSV no tiene filas: no hay nada que medir.")
    result = evaluate(rows, args.tolerance)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
