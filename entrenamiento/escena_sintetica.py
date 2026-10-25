"""Escenas sintéticas para ajustar parámetros sin hardware: personas en un salón y los errores de un detector real.

Las coordenadas son las del piso (las mismas que produce la homografía del borde y que usa la rejilla de puestos del
backend): x de 0 a 1 de izquierda a derecha, y de 0 (tablero) a 1 (fondo). Los pupitres ocupan la franja
``y ∈ [0,30; 0,95]``; delante queda la zona del docente. No envían nada a ningún servicio.
"""
from __future__ import annotations

from dataclasses import dataclass
import random

IZQUIERDA, DERECHA, ARRIBA, ABAJO = 0.05, 0.95, 0.30, 0.95


@dataclass(frozen=True)
class Salon:
    space_id: str
    filas: int
    columnas: int
    area_sqm: float
    capacidad: int

    def centro(self, fila: int, columna: int) -> tuple[float, float]:
        """Centro del puesto (fila, columna) empezando en 1, igual que la rejilla del backend."""
        ancho = (DERECHA - IZQUIERDA) / self.columnas
        alto = (ABAJO - ARRIBA) / self.filas
        return IZQUIERDA + (columna - 0.5) * ancho, ARRIBA + (fila - 0.5) * alto

    def puestos_desde_el_fondo(self) -> list[tuple[int, int]]:
        """Orden en que se sientan los estudiantes: primero la última fila, como en la piloto."""
        return [(f, c) for f in range(self.filas, 0, -1) for c in range(1, self.columnas + 1)]


@dataclass(frozen=True)
class Ruido:
    """Errores de un detector real: personas que no ve, posiciones imprecisas y falsas detecciones de baja confianza."""
    perdida: float = 0.05
    desplazamiento: float = 0.01
    falsos: float = 0.05


@dataclass(frozen=True)
class Persona:
    track: int
    x: float
    y: float
    confianza: float
    docente: bool
    real: bool


def personas(salon: Salon, docentes: int, estudiantes: int, de_pie: int, ruido: Ruido,
             rng: random.Random) -> list[Persona]:
    """Las personas que la escena contiene y lo que el detector reporta de ellas, falsas incluidas."""
    reales: list[tuple[float, float, bool]] = []
    for i in range(docentes):
        reales.append((0.35 + 0.3 * i, 0.15, True))
    for fila, columna in salon.puestos_desde_el_fondo()[:estudiantes]:
        x, y = salon.centro(fila, columna)
        reales.append((x, y, False))
    for i in range(de_pie):  # sin puesto: en los pasillos del fondo
        reales.append((0.02 + 0.96 * (i + 0.5) / max(1, de_pie), 0.97, False))
    vistas = []
    for track, (x, y, docente) in enumerate(reales, start=1):
        if rng.random() < ruido.perdida:
            continue
        vistas.append(Persona(track, _limitar(x + rng.gauss(0, ruido.desplazamiento)),
                              _limitar(y + rng.gauss(0, ruido.desplazamiento)), rng.uniform(0.6, 0.95), docente, True))
    if rng.random() < ruido.falsos:
        vistas.append(Persona(1000 + rng.randrange(1000), rng.uniform(0.05, 0.95), rng.uniform(0.05, 0.95),
                              rng.uniform(0.25, 0.5), False, False))
    return vistas


def _limitar(valor: float) -> float:
    return min(1.0, max(0.0, valor))
