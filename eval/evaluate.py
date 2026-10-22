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


def _number(row: dict, column: str, line: int, minimum: float, maximum: float) -> float:
    try:
        value = float(row[column])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"fila {line}: {column} debe ser un número") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"fila {line}: {column} debe estar entre {minimum} y {maximum}")
    return value


def _integer(row: dict, column: str, line: int, minimum: int, maximum: int) -> int:
    try:
        value = int(row[column])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"fila {line}: {column} debe ser un entero") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"fila {line}: {column} debe estar entre {minimum} y {maximum}")
    return value


def nonnegative_finite(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("debe ser un número finito no negativo") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("debe ser un número finito no negativo")
    return parsed


def evaluate(rows: list[dict], tolerance: float) -> dict:
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance debe ser un número finito no negativo")
    filters: dict[str, KalmanOccupancy] = defaultdict(KalmanOccupancy)
    per_space_errors: dict[str, list[float]] = defaultdict(list)
    all_errors, with_camera, without_camera = [], [], []
    calibration = {bin_: [0, 0] for bin_ in BINS}
    for line, row in enumerate(rows, start=2):
        missing = [column for column in REQUIRED if row.get(column, "") == ""]
        if missing:
            raise ValueError(f"fila {line}: faltan {', '.join(missing)}")
        space_id = row["space_id"].strip()
        if not space_id:
            raise ValueError(f"fila {line}: space_id no puede estar vacío")
        yolo = row.get("yolo_people", "")
        yolo_people = _integer(row, "yolo_people", line, 0, 1000) if yolo != "" else None
        outdoor = _number(row, "outdoor_co2_ppm", line, 300, 1000) if row.get("outdoor_co2_ppm") else 415.0
        co2 = _number(row, "co2_ppm", line, 0, 10000)
        wifi = _integer(row, "wifi_devices", line, 0, 10000)
        true_people = _integer(row, "true_people", line, 0, 1000)
        estimate, confidence = filters[space_id].update(yolo_people, co2, wifi, outdoor)
        error = estimate - true_people
        all_errors.append(error)
        per_space_errors[space_id].append(error)
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


def read_rows(handle) -> list[dict]:
    reader = csv.DictReader(handle)
    headers = reader.fieldnames
    if not headers:
        raise ValueError("el CSV debe incluir un encabezado")
    duplicates = sorted({header for header in headers if headers.count(header) > 1})
    if duplicates:
        raise ValueError(f"encabezados duplicados: {', '.join(duplicates)}")
    missing = [column for column in REQUIRED if column not in headers]
    if missing:
        raise ValueError(f"faltan columnas requeridas: {', '.join(missing)}")
    rows = []
    for line, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"fila {line}: hay más valores que encabezados")
        if any(value is None for value in row.values()):
            raise ValueError(f"fila {line}: hay menos valores que encabezados")
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--tolerance", type=nonnegative_finite, default=2.0, help="personas de error aceptadas")
    parser.add_argument("--json", type=Path, help="guardar el resultado en este archivo")
    args = parser.parse_args()
    try:
        with args.csv.open(newline="", encoding="utf-8-sig") as handle:
            rows = read_rows(handle)
    except (OSError, ValueError) as exc:
        parser.error(f"no se pudo leer el CSV: {exc}")
    if not rows:
        sys.exit("El CSV no tiene filas: no hay nada que medir.")
    try:
        result = evaluate(rows, args.tolerance)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
