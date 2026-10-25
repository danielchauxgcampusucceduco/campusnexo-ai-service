#!/usr/bin/env python3
"""Compuerta de atributos de calidad: decide si un modelo o un ajuste puede pasar a la piloto.

Lee las métricas medidas (JSON) y las compara con ``atributos_calidad.json``. Solo se evalúan los atributos que la
medición trae: el ajuste sin cámara mide conteo y docente; un YOLO reentrenado mide además recall, precisión e
inferencia. Sale con código 1 si alguno falla, para que un script o la CI no promueva un modelo peor.

    python -m entrenamiento.compuerta_calidad metricas.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

UMBRALES = Path(__file__).with_name("atributos_calidad.json")
# Cada métrica medida, con el umbral que le corresponde y si el umbral es un máximo o un mínimo.
REGLAS = {
    "mae_conteo": ("mae_conteo_max", "max"),
    "tasa_docente": ("tasa_docente_min", "min"),
    "recall_persona": ("recall_persona_min", "min"),
    "precision_persona": ("precision_persona_min", "min"),
    "inferencia_ms": ("inferencia_ms_max", "max"),
}


def evaluar(metricas: dict, umbrales: dict) -> list[tuple[str, float, float, bool]]:
    """(métrica, valor, umbral, cumple) de cada atributo presente en la medición."""
    resultado = []
    for metrica, (clave, sentido) in REGLAS.items():
        if metrica not in metricas:
            continue
        valor, umbral = float(metricas[metrica]), float(umbrales[clave])
        resultado.append((metrica, valor, umbral, valor <= umbral if sentido == "max" else valor >= umbral))
    if not resultado:
        raise ValueError("La medición no trae ninguna métrica de calidad conocida")
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("metricas", help="JSON con las métricas medidas")
    parser.add_argument("--umbrales", default=str(UMBRALES))
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa otra página de códigos
    metricas = json.loads(Path(args.metricas).read_text(encoding="utf-8"))
    umbrales = json.loads(Path(args.umbrales).read_text(encoding="utf-8"))
    resultado = evaluar(metricas, umbrales)
    for metrica, valor, umbral, cumple in resultado:
        print(f"{'✔' if cumple else '✘'} {metrica}: {valor:.3f} (umbral {umbral:g})")
    aprobado = all(cumple for *_, cumple in resultado)
    print("APROBADO" if aprobado else "RECHAZADO")
    return 0 if aprobado else 1


if __name__ == "__main__":
    sys.exit(main())
