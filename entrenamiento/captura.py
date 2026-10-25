#!/usr/bin/env python3
"""Captura de imágenes para reentrenar YOLO, solo en sesiones con consentimiento.

Guarda un frame cada ``--cada`` segundos en ``datasets/salas/sin_etiquetar/<sesion>/`` (fuera de git) para etiquetarlo
después en CVAT o Label Studio con las clases de ``dataset.yaml``. Exige ``--consentimiento`` con el identificador del
acta firmada por quienes aparecerán (Ley 1581 de 2012): sin él no captura nada.

    python -m entrenamiento.captura --source 0 --sesion 301A-2026-11-03-manana --consentimiento ACTA-017 --minutos 20
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

DESTINO = Path(__file__).resolve().parent / "datasets" / "salas" / "sin_etiquetar"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True)
    parser.add_argument("--sesion", required=True, help="salón, fecha y franja, p. ej. 301A-2026-11-03-manana")
    parser.add_argument("--consentimiento", required=True, help="identificador del acta de consentimiento")
    parser.add_argument("--cada", type=float, default=5.0)
    parser.add_argument("--minutos", type=float, default=20.0)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not args.consentimiento.strip():
        raise SystemExit("Sin acta de consentimiento no se captura")

    import cv2  # dependencia opcional: extra "vision"

    carpeta = DESTINO / args.sesion
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "sesion.json").write_text(json.dumps({
        "sesion": args.sesion, "consentimiento": args.consentimiento,
        "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2), encoding="utf-8")
    captura = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    guardadas, fin = 0, time.monotonic() + args.minutos * 60
    while time.monotonic() < fin:
        ok, imagen = captura.read()
        if not ok:
            break
        cv2.imwrite(str(carpeta / f"{guardadas:05d}.jpg"), imagen)
        guardadas += 1
        time.sleep(args.cada)
    captura.release()
    print(f"{guardadas} imágenes en {carpeta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
