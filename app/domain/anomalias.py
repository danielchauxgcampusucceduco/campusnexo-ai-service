"""Salud de los sensores: lecturas que un sensor sano no produciría.

Tres señales, por salón y por sensor, sobre la serie ordenada en el tiempo:

* **FUERA_DE_RANGO**: valores físicamente imposibles para un salón (CO₂ bajo el aire exterior, humedad sobre
  100 %, …): sensor dañado, mal conectado o mal calibrado.
* **VALOR_PEGADO**: un sensor analógico (CO₂, temperatura, humedad) siempre oscila un poco; el mismo valor
  exacto muchas lecturas seguidas indica un sensor congelado o un firmware que repite la última lectura. Luz y
  potencia quedan fuera: un salón apagado reporta 0 durante horas y está bien.
* **SALTO**: un cambio entre lecturas consecutivas muy por encima de la variación típica de esa serie. La
  variación típica se mide con la MAD (desviación absoluta mediana) de las diferencias, robusta a los propios
  saltos; un piso por sensor evita alarmar por ruido en series casi planas.

No corrige ni descarta datos: señala, y el administrador decide.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import numpy as np

RANGOS = {
    "co2_ppm": (300.0, 5000.0),
    "temperature_c": (-5.0, 45.0),
    "humidity_pct": (0.0, 100.0),
    "illuminance_lux": (0.0, 100_000.0),
    "active_power_kw": (0.0, 200.0),
}
ANALOGICOS = ("co2_ppm", "temperature_c", "humidity_pct")
LECTURAS_PEGADAS = 12
UMBRAL_SALTO = 8.0
# Variación mínima que se considera ruido normal de cada sensor entre dos lecturas.
PISO_VARIACION = {"co2_ppm": 15.0, "temperature_c": 0.3, "humidity_pct": 1.5, "illuminance_lux": 50.0,
                  "active_power_kw": 0.2}
MIN_LECTURAS_SALTO = 10
MAD_A_SIGMA = 1.4826


@dataclass(frozen=True)
class Lectura:
    space_id: str
    timestamp: datetime
    valores: dict[str, float]


@dataclass(frozen=True)
class Anomalia:
    space_id: str
    sensor: str
    timestamp: datetime
    tipo: str
    valor: float
    detalle: str


def detectar(lecturas: list[Lectura]) -> list[Anomalia]:
    """Anomalías de todas las lecturas, en orden de salón, sensor y tiempo."""
    por_salon: dict[str, list[Lectura]] = defaultdict(list)
    for lectura in lecturas:
        por_salon[lectura.space_id].append(lectura)
    anomalias: list[Anomalia] = []
    for space_id in sorted(por_salon):
        serie = sorted(por_salon[space_id], key=lambda lectura: lectura.timestamp)
        tiempos = [lectura.timestamp for lectura in serie]
        for sensor in RANGOS:
            valores = np.array([lectura.valores[sensor] for lectura in serie], dtype=float)
            anomalias += _fuera_de_rango(space_id, sensor, tiempos, valores)
            if sensor in ANALOGICOS:
                anomalias += _pegado(space_id, sensor, tiempos, valores)
            anomalias += _saltos(space_id, sensor, tiempos, valores)
    return anomalias


def _fuera_de_rango(space_id, sensor, tiempos, valores) -> list[Anomalia]:
    bajo, alto = RANGOS[sensor]
    return [Anomalia(space_id, sensor, tiempos[i], "FUERA_DE_RANGO", float(valores[i]),
                     f"fuera de {bajo:g}–{alto:g}")
            for i in np.flatnonzero((valores < bajo) | (valores > alto))]


def _pegado(space_id, sensor, tiempos, valores) -> list[Anomalia]:
    """Una anomalía por racha: en la lectura que completa {LECTURAS_PEGADAS} valores idénticos seguidos."""
    anomalias, racha = [], 1
    for i in range(1, len(valores)):
        racha = racha + 1 if valores[i] == valores[i - 1] else 1
        if racha == LECTURAS_PEGADAS:
            anomalias.append(Anomalia(space_id, sensor, tiempos[i], "VALOR_PEGADO", float(valores[i]),
                                      f"{LECTURAS_PEGADAS} lecturas idénticas seguidas"))
    return anomalias


def _saltos(space_id, sensor, tiempos, valores) -> list[Anomalia]:
    if len(valores) < MIN_LECTURAS_SALTO:
        return []
    diferencias = np.diff(valores)
    mediana = float(np.median(diferencias))
    escala = max(MAD_A_SIGMA * float(np.median(np.abs(diferencias - mediana))), PISO_VARIACION[sensor])
    puntajes = np.abs(diferencias - mediana) / escala
    return [Anomalia(space_id, sensor, tiempos[i + 1], "SALTO", float(valores[i + 1]),
                     f"cambio de {diferencias[i]:+.1f} ({puntajes[i]:.0f} veces la variación típica)")
            for i in np.flatnonzero(puntajes > UMBRAL_SALTO)]
