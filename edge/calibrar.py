#!/usr/bin/env python3
"""Calibración de la cámara de un salón: una vez, al instalarla.

Muestra un frame de la cámara y pide marcar con clic las cuatro esquinas del piso en este orden: adelante-izquierda,
adelante-derecha, atrás-derecha, atrás-izquierda ("adelante" es el lado del tablero). Guarda las esquinas en
coordenadas normalizadas de la imagen; ``homografia.cargar`` las convierte en la proyección al piso. El frame se
muestra solo en pantalla y no se guarda.

    python -m edge.calibrar --space-id 301-A --source 0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from edge import homografia

ORDEN = ("adelante-izquierda", "adelante-derecha", "atrás-derecha", "atrás-izquierda")


def main() -> None:
    import cv2  # dependencia opcional: extra "vision"

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--source", required=True, help="índice de cámara, URL RTSP o ruta de video")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa otra página de códigos

    captura = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    ok, imagen = captura.read()
    captura.release()
    if not ok:
        raise SystemExit("No se pudo leer la cámara")
    alto, ancho = imagen.shape[:2]
    esquinas: list[list[float]] = []

    def marcar(evento, x, y, _flags, _datos):
        if evento == cv2.EVENT_LBUTTONDOWN and len(esquinas) < 4:
            esquinas.append([round(x / ancho, 4), round(y / alto, 4)])
            cv2.circle(imagen, (x, y), 6, (0, 172, 201), -1)

    ventana = "Marca las esquinas del piso"
    cv2.namedWindow(ventana)
    cv2.setMouseCallback(ventana, marcar)
    while len(esquinas) < 4:
        texto = f"Clic en la esquina {ORDEN[len(esquinas)]} (Esc para salir)"
        vista = imagen.copy()
        cv2.putText(vista, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow(ventana, vista)
        if cv2.waitKey(30) == 27:
            raise SystemExit("Calibración cancelada")
    cv2.destroyAllWindows()

    homografia.calcular(esquinas, homografia.ESQUINAS_PISO)  # falla aquí si tres esquinas quedaron alineadas
    destino = Path(f"calibracion-{args.space_id.replace('-', '')}.json")
    destino.write_text(json.dumps({"space_id": args.space_id, "esquinas_imagen": esquinas,
                                   "esquinas_piso": homografia.ESQUINAS_PISO}, indent=2), encoding="utf-8")
    print(f"Calibración guardada en {destino}")


if __name__ == "__main__":
    main()
