"""Proyección de la imagen de la cámara al piso del salón (homografía de 4 puntos).

La cámara está en una esquina, inclinada: un pupitre del fondo se ve más pequeño y más arriba que uno de adelante.
Con las cuatro esquinas del piso marcadas una vez en la imagen (``calibrar.py``), cada punto de la imagen pasa a
coordenadas normalizadas del piso: x de 0 a 1 de izquierda a derecha y y de 0 (tablero) a 1 (pared del fondo),
las mismas que usa la rejilla de puestos del backend.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# Esquinas del piso en orden: adelante-izquierda, adelante-derecha, atrás-derecha, atrás-izquierda.
ESQUINAS_PISO = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


def calcular(origen, destino) -> np.ndarray:
    """Matriz 3 × 3 que lleva los 4 puntos de ``origen`` a los de ``destino`` (DLT con h33 = 1)."""
    origen = np.asarray(origen, dtype=float)
    destino = np.asarray(destino, dtype=float)
    if origen.shape != (4, 2) or destino.shape != (4, 2):
        raise ValueError("Se necesitan exactamente 4 puntos de origen y 4 de destino")
    filas, valores = [], []
    for (x, y), (u, v) in zip(origen, destino):
        filas.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        filas.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        valores += [u, v]
    try:
        h = np.linalg.solve(np.array(filas), np.array(valores))
    except np.linalg.LinAlgError as exc:
        raise ValueError("Tres de las cuatro esquinas están alineadas: vuelve a marcarlas") from exc
    return np.append(h, 1.0).reshape(3, 3)


def aplicar(matriz: np.ndarray, puntos) -> np.ndarray:
    """Proyecta puntos (N × 2) con la homografía."""
    puntos = np.asarray(puntos, dtype=float).reshape(-1, 2)
    homogeneos = np.hstack([puntos, np.ones((len(puntos), 1))]) @ matriz.T
    return homogeneos[:, :2] / homogeneos[:, 2:3]


def cargar(ruta: str | Path) -> tuple[str, np.ndarray]:
    """(space_id, homografía imagen → piso) de un archivo de ``calibrar.py``."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return datos["space_id"], calcular(datos["esquinas_imagen"], datos.get("esquinas_piso", ESQUINAS_PISO))
