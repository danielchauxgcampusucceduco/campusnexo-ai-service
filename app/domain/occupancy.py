"""Estimación de ocupación por fusión de mediciones: el mismo modelo que el gemelo digital en Java.

Tres fuentes, cada una con su incertidumbre:

* conteo de la cámara (YOLO en el borde), cuando llega: varianza 0,64 personas²;
* CO₂ por balance de masa en estado estable: ``(co2 − exterior) · área / 1000`` personas, con error
  relativo de 35 % (más 2 personas de piso);
* dispositivos Wi-Fi a 0,8 personas por dispositivo, con error relativo de 30 % (más 2 de piso).

La estimación es la media ponderada por el inverso de la varianza de las fuentes disponibles: es la
actualización de Kalman desde una creencia previa no informada. El servicio **no guarda estado** entre
peticiones, así que un reintento del backend nunca aplica dos veces la misma medición y cualquier réplica
responde lo mismo. ``confidence_pct = (1 − σ / capacidad) · 100``: cuánto margen de error tiene la
estimación en relación con el tamaño del salón; **no** es la probabilidad de acertar.

Los parámetros son los del backend (``app.twin.kalman`` en ``application.yml``) y ambos repositorios
prueban los mismos casos de referencia (``tests/fusion_golden_cases.csv``). Son valores ilustrativos hasta
medirlos con conteos reales (``eval/evaluate.py``).
"""
from __future__ import annotations

from dataclasses import dataclass
import math

CAMERA_VARIANCE = 0.64
CO2_RELATIVE_ERROR = 0.35
WIFI_RELATIVE_ERROR = 0.30
PEOPLE_PER_DEVICE = 0.8
CO2_PPM_PER_PERSON_SQM = 1000.0
MIN_VARIANCE = 1.0
ERROR_FLOOR_PEOPLE = 2.0


@dataclass(frozen=True)
class SourceContribution:
    source: str
    people: float
    variance: float
    weight: float


@dataclass(frozen=True)
class Fusion:
    estimate: float
    sigma: float
    sources: tuple[SourceContribution, ...]

    def people(self) -> int:
        return max(0, math.floor(self.estimate + 0.5))

    def confidence_pct(self, capacity: int) -> float:
        return confidence_pct(self.sigma, capacity)


def _finite(name: str, value: float, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or not low <= value <= high:
        raise ValueError(f"{name} debe estar entre {low} y {high}")
    return float(value)


def _count(name: str, value: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= high:
        raise ValueError(f"{name} debe ser un entero entre 0 y {high}")
    return value


def _relative_variance(people: float, relative_error: float) -> float:
    sigma = relative_error * people + ERROR_FLOOR_PEOPLE
    return max(MIN_VARIANCE, sigma * sigma)


def fuse_occupancy(camera_people: int | None, co2_ppm: float, wifi_devices: int, area_sqm: float,
                   outdoor_co2_ppm: float = 420.0) -> Fusion:
    """Fusiona una lectura sin estado previo. Lanza ``ValueError`` si alguna medición es inválida."""
    if camera_people is not None:
        _count("camera_people", camera_people, 1000)
    co2 = _finite("co2_ppm", co2_ppm, 0, 10000)
    _count("wifi_devices", wifi_devices, 10000)
    area = _finite("area_sqm", area_sqm, 0.1, 100000)
    outdoor = _finite("outdoor_co2_ppm", outdoor_co2_ppm, 300, 1000)

    observations: list[tuple[str, float, float]] = []
    if camera_people is not None:
        observations.append(("camara_yolo", float(camera_people), CAMERA_VARIANCE))
    from_co2 = max(0.0, co2 - outdoor) * area / CO2_PPM_PER_PERSON_SQM
    observations.append(("co2_balance_masico", from_co2, _relative_variance(from_co2, CO2_RELATIVE_ERROR)))
    from_wifi = wifi_devices * PEOPLE_PER_DEVICE
    observations.append(("wifi_dispositivos", from_wifi, _relative_variance(from_wifi, WIFI_RELATIVE_ERROR)))

    information = sum(1 / variance for _, _, variance in observations)
    estimate = max(0.0, sum(people / variance for _, people, variance in observations) / information)
    sources = tuple(SourceContribution(name, round(people, 3), round(variance, 3), round((1 / variance) / information, 4))
                    for name, people, variance in observations)
    return Fusion(estimate, math.sqrt(1 / information), sources)


def confidence_pct(sigma: float, capacity: int) -> float:
    """``(1 − σ / capacidad) · 100`` en [0, 100], con una cifra decimal. No es una probabilidad."""
    if not math.isfinite(sigma) or sigma < 0:
        raise ValueError("sigma debe ser finita y no negativa")
    _count("capacity", capacity, 5000)
    # Half up, like Java's Math.round, so both implementations give the same digit.
    return math.floor(max(0.0, 1 - sigma / max(1, capacity)) * 1000 + 0.5) / 10.0
