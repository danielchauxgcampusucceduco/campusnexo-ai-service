"""Puestos de trabajo vistos por la cámara: descubrimiento, auditoría y emparejamiento con su computador.

Las posiciones están en coordenadas normalizadas del piso del salón (x de izquierda a derecha, y desde el tablero
hacia el fondo, ambas en [0, 1]), ya proyectadas con la homografía de la calibración. Así una fila de puestos es
una franja de ``y`` sin importar la perspectiva de la cámara en la esquina.

* **Descubrir**: con el salón vacío, el monitor es el ancla de cada puesto (YOLO lo reconoce bien como ``tv``);
  la silla y la mesa más cercanas a cada monitor completan el puesto. Los monitores se agrupan en filas por
  saltos en ``y`` y cada fila se ordena por ``x``: A1 es el primer puesto de la fila más cercana al tablero.
* **Auditar**: con los puestos ya conocidos, qué silla y qué mesa siguen viéndose junto a cada monitor.
* **Emparejar**: cuando un computador muestra su patrón a pantalla completa, la región de su monitor cambia de
  brillo mucho más que las demás; esa región dice en qué puesto está.

YOLO COCO distingue mal un escritorio (``dining table``), por eso un puesto sin mesa se propone igual, marcado
como incompleto para que el administrador lo revise.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

# Clases COCO que se usan como mobiliario (la persona, 0, la cuenta el publicador aparte).
COCO_MOBILIARIO = {56: "silla", 60: "mesa", 62: "monitor", 63: "laptop"}
SEPARACION_FILAS = 0.06
ALCANCE = 0.12
RADIO_CONSOLIDACION = 0.03


@dataclass(frozen=True)
class Objeto:
    clase: str
    x: float
    y: float


@dataclass(frozen=True)
class PuestoVisto:
    fila: int
    columna: int
    x: float
    y: float
    monitor: bool
    silla: bool
    mesa: bool

    @property
    def etiqueta(self) -> str:
        return chr(ord("A") + self.fila - 1) + str(self.columna)


def consolidar(frames: list[list[Objeto]], radio: float = RADIO_CONSOLIDACION) -> list[Objeto]:
    """Objetos estables: los que aparecen en al menos la mitad de los frames, con su posición promedio.

    Varios frames del salón vacío eliminan detecciones fugaces (una sombra, un reflejo)."""
    if not frames:
        return []
    grupos: list[list[Objeto]] = []
    for frame in frames:
        for objeto in frame:
            grupo = next((g for g in grupos if g[0].clase == objeto.clase
                          and math.dist((g[0].x, g[0].y), (objeto.x, objeto.y)) <= radio), None)
            if grupo is None:
                grupos.append([objeto])
            else:
                grupo.append(objeto)
    minimo = math.ceil(len(frames) / 2)
    return [Objeto(g[0].clase, float(np.mean([o.x for o in g])), float(np.mean([o.y for o in g])))
            for g in grupos if len(g) >= minimo]


def descubrir(objetos: list[Objeto], separacion_filas: float = SEPARACION_FILAS,
              alcance: float = ALCANCE) -> list[PuestoVisto]:
    """Un puesto por monitor, en filas y columnas, con la silla y la mesa más cercanas a cada uno."""
    monitores = sorted((o for o in objetos if o.clase == "monitor"), key=lambda o: o.y)
    filas: list[list[Objeto]] = []
    for monitor in monitores:
        if filas and monitor.y - filas[-1][-1].y <= separacion_filas:
            filas[-1].append(monitor)
        else:
            filas.append([monitor])
    sillas = [o for o in objetos if o.clase == "silla"]
    mesas = [o for o in objetos if o.clase == "mesa"]
    puestos = []
    for numero_fila, fila in enumerate(filas, start=1):
        for numero_columna, monitor in enumerate(sorted(fila, key=lambda o: o.x), start=1):
            puestos.append(PuestoVisto(numero_fila, numero_columna, monitor.x, monitor.y, True,
                                       _tomar_cercano(monitor, sillas, alcance), _tomar_cercano(monitor, mesas, alcance)))
    return puestos


def auditar(puestos: list[PuestoVisto], objetos: list[Objeto], alcance: float = ALCANCE) -> list[PuestoVisto]:
    """Los puestos conocidos con la silla y la mesa que se ven ahora junto a cada uno."""
    sillas = [o for o in objetos if o.clase == "silla"]
    mesas = [o for o in objetos if o.clase == "mesa"]
    referencia = [Objeto("monitor", p.x, p.y) for p in puestos]
    return [PuestoVisto(p.fila, p.columna, p.x, p.y, p.monitor, _tomar_cercano(m, sillas, alcance),
                        _tomar_cercano(m, mesas, alcance)) for p, m in zip(puestos, referencia)]


def _tomar_cercano(ancla: Objeto, candidatos: list[Objeto], alcance: float) -> bool:
    """Toma (y quita de la lista) el candidato más cercano dentro del alcance: cada silla sirve a un solo puesto."""
    if not candidatos:
        return False
    distancias = [math.dist((ancla.x, ancla.y), (c.x, c.y)) for c in candidatos]
    indice = int(np.argmin(distancias))
    if distancias[indice] > alcance:
        return False
    candidatos.pop(indice)
    return True


def patron_visto(antes: np.ndarray, despues: np.ndarray, regiones: list[tuple[int, int, int, int]],
                 umbral: float = 40.0) -> int | None:
    """Índice de la región (x0, y0, x1, y1 en píxeles) cuyo brillo cambió claramente más que las demás, o None.

    ``antes`` y ``despues`` son imágenes en escala de grises del mismo tamaño. Exige un cambio medio de al menos
    ``umbral`` niveles y el doble que la segunda región, para no confundir el patrón con alguien que pasa."""
    if antes.shape != despues.shape or not regiones:
        raise ValueError("Se necesitan dos imágenes del mismo tamaño y al menos una región")
    diferencia = np.abs(despues.astype(float) - antes.astype(float))
    cambios = np.array([diferencia[y0:y1, x0:x1].mean() if (x1 > x0 and y1 > y0) else 0.0
                        for x0, y0, x1, y1 in regiones])
    orden = np.argsort(cambios)[::-1]
    mayor = cambios[orden[0]]
    segundo = cambios[orden[1]] if len(cambios) > 1 else 0.0
    if mayor < umbral or mayor < 2 * segundo:
        return None
    return int(orden[0])
