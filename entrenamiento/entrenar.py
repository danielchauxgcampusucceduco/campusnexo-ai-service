#!/usr/bin/env python3
"""Ajuste fino de YOLO con las imágenes etiquetadas de las salas, detrás de la compuerta de calidad.

Parte de los pesos COCO (transferencia de aprendizaje), entrena con ``dataset.yaml`` y valida en el conjunto de prueba.
Escribe ``metricas-yolo.json`` con recall y precisión de la clase persona y el tiempo de inferencia, y solo copia los
pesos a ``modelos/`` si ``compuerta_calidad`` los aprueba. Necesita GPU para un tiempo razonable (local o Colab).

    python -m entrenamiento.entrenar --modelo yolo11n.pt --epocas 100 --imgsz 1280
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from entrenamiento import compuerta_calidad

AQUI = Path(__file__).resolve().parent
PERSONA = 0


def metricas_de(validacion) -> dict:
    """Recall y precisión de la clase persona e inferencia por imagen, del resultado de ``model.val`` de Ultralytics."""
    caja = validacion.box
    return {"recall_persona": round(float(caja.r[PERSONA]), 4), "precision_persona": round(float(caja.p[PERSONA]), 4),
            "map50": round(float(caja.map50), 4), "inferencia_ms": round(float(validacion.speed["inference"]), 1)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default="yolo11n.pt", help="pesos de partida (COCO)")
    parser.add_argument("--epocas", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=1280, help="grande para ver a los estudiantes del fondo")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    from ultralytics import YOLO  # dependencia opcional: extra "vision"

    modelo = YOLO(args.modelo)
    modelo.train(data=str(AQUI / "dataset.yaml"), epochs=args.epocas, imgsz=args.imgsz, project=str(AQUI / "runs"),
                 name="salas", exist_ok=True)
    metricas = metricas_de(modelo.val(data=str(AQUI / "dataset.yaml"), split="test", imgsz=args.imgsz))
    archivo = AQUI / "metricas-yolo.json"
    archivo.write_text(json.dumps(metricas, indent=2), encoding="utf-8")
    if compuerta_calidad.main([str(archivo)]) != 0:
        print("El modelo no cumple los atributos de calidad: no se promueve")
        return 1
    destino = AQUI / "modelos"
    destino.mkdir(exist_ok=True)
    shutil.copy(Path(modelo.trainer.best), destino / "salas.pt")
    print(f"Modelo promovido a {destino / 'salas.pt'}: úsalo con YOLO_MODEL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
