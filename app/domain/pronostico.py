"""Pronóstico de ocupación por franja horaria, aprendido del historial del propio salón.

Los salones siguen el horario de clases: el lunes a las 10 se parece a los lunes a las 10 anteriores. El modelo
es un **perfil semanal suavizado**:

1. El historial (cada cambio guardado por el gemelo) se agrupa en horas locales y se promedia cada hora.
2. Para cada franja (día de la semana, hora) se calcula la media y la desviación ponderando cada semana con
   ``PESO_SEMANAL ** semanas_atras``: las semanas recientes pesan más (suavizado exponencial entre semanas).
3. Si una franja no tiene datos, se usa la misma hora de cualquier día y, si tampoco, la media del salón.

El intervalo ``[low, high]`` es la media ± 1,28 σ (≈ 80 % si los errores fueran normales), recortado a
``[0, capacidad]``. No guarda estado entre peticiones: el backend envía el historial cada vez.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

PESO_SEMANAL = 0.6
Z_80 = 1.28
METODO = "perfil_semanal_suavizado"


@dataclass(frozen=True)
class Punto:
    timestamp: datetime
    people: float
    low: float
    high: float


@dataclass(frozen=True)
class Pronostico:
    metodo: str
    muestras: int
    puntos: list[Punto]


def pronosticar(historial: list[tuple[datetime, int]], capacidad: int, horas: int, zona: str) -> Pronostico:
    """``historial``: (instante con zona horaria, personas). Lanza ``ValueError`` si no hay historial o la zona no existe."""
    if not historial:
        raise ValueError("Se necesita historial para pronosticar")
    if capacidad < 1 or not 1 <= horas <= 48:
        raise ValueError("capacidad debe ser positiva y horas estar entre 1 y 48")
    tz = ZoneInfo(zona)
    por_hora: dict[datetime, list[int]] = defaultdict(list)
    for instante, personas in historial:
        local = instante.astimezone(tz).replace(minute=0, second=0, microsecond=0)
        por_hora[local].append(personas)
    horas_vistas = {hora: float(np.mean(valores)) for hora, valores in por_hora.items()}
    ultima = max(horas_vistas)

    franja: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    hora_del_dia: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for hora, media in horas_vistas.items():
        peso = PESO_SEMANAL ** ((ultima - hora).days // 7)
        franja[(hora.weekday(), hora.hour)].append((media, peso))
        hora_del_dia[hora.hour].append((media, peso))
    todas = [(media, 1.0) for media in horas_vistas.values()]

    puntos = []
    inicio = ultima + timedelta(hours=1)
    for paso in range(horas):
        local = inicio + timedelta(hours=paso)
        muestras = franja.get((local.weekday(), local.hour)) or hora_del_dia.get(local.hour) or todas
        media, desviacion = _media_ponderada(muestras)
        puntos.append(Punto(local.astimezone(timezone.utc), round(_recortar(media, capacidad), 2),
                            round(_recortar(media - Z_80 * desviacion, capacidad), 2),
                            round(_recortar(media + Z_80 * desviacion, capacidad), 2)))
    return Pronostico(METODO, len(historial), puntos)


def _media_ponderada(muestras: list[tuple[float, float]]) -> tuple[float, float]:
    valores = np.array([valor for valor, _ in muestras])
    pesos = np.array([peso for _, peso in muestras])
    media = float(np.average(valores, weights=pesos))
    return media, float(np.sqrt(np.average((valores - media) ** 2, weights=pesos)))


def _recortar(valor: float, capacidad: int) -> float:
    return min(float(capacidad), max(0.0, valor))
