"""Estimación ligera de ocupación por fusión de señales.

Qué es: un filtro de Kalman **escalar** (un solo estado: personas en el espacio) con parámetros fijos.
Cada lectura combina tres indicadores con pesos fijos:

* conteo de la cámara (YOLO en el borde), cuando llega;
* CO₂ sobre el exterior, convertido a personas con un factor fijo (14,5 ppm por persona);
* dispositivos Wi-Fi, a 0,88 personas por dispositivo.

Qué no es: un modelo entrenado ni calibrado. Los pesos, factores y varianzas son valores iniciales de
demostración. ``confidence_pct`` se deriva de la varianza interna del filtro (``(1 - P/5)·100``): indica
cuánto se ha estabilizado el filtro, **no** la probabilidad de acertar. Para hablar de precisión hay que
medir el error contra conteos reales (``eval/evaluate.py``).
"""
from dataclasses import dataclass
import math

CO2_PPM_PER_PERSON = 14.5
PEOPLE_PER_WIFI_DEVICE = 0.88
WEIGHTS_WITH_CAMERA = (0.76, 0.14, 0.10)
WEIGHTS_WITHOUT_CAMERA = (0.65, 0.35)
NO_CAMERA_VARIANCE_FACTOR = 3.5


@dataclass
class KalmanOccupancy:
    process_variance: float = 0.35
    measurement_variance: float = 1.8
    estimate: float = 0.0
    variance: float = 1.0

    def __post_init__(self) -> None:
        for name in ("process_variance", "measurement_variance", "estimate", "variance"):
            value = getattr(self, name)
            if not math.isfinite(value):
                raise ValueError(f"{name} debe ser finito")
        if self.process_variance < 0 or self.measurement_variance <= 0 or self.variance < 0:
            raise ValueError("Las varianzas deben ser no negativas y la varianza de medición positiva")
        if self.estimate < 0:
            raise ValueError("estimate debe ser no negativo")

    def update(self, yolo_count: int | None, co2_ppm: float, wifi_devices: int,
               outdoor_co2_ppm: float = 415.0) -> tuple[int, float]:
        if yolo_count is not None and (
            isinstance(yolo_count, bool) or not isinstance(yolo_count, int) or yolo_count < 0
        ):
            raise ValueError("yolo_count debe ser un entero no negativo o None")
        if isinstance(wifi_devices, bool) or not isinstance(wifi_devices, int) or wifi_devices < 0:
            raise ValueError("wifi_devices debe ser un entero no negativo")
        if not math.isfinite(co2_ppm) or co2_ppm < 0:
            raise ValueError("co2_ppm debe ser finito y no negativo")
        if not math.isfinite(outdoor_co2_ppm) or outdoor_co2_ppm < 0:
            raise ValueError("outdoor_co2_ppm debe ser finito y no negativo")
        co2_estimate = max(0.0, (co2_ppm - outdoor_co2_ppm) / CO2_PPM_PER_PERSON)
        wifi_estimate = max(0, wifi_devices) * PEOPLE_PER_WIFI_DEVICE
        if yolo_count is not None:
            camera_w, co2_w, wifi_w = WEIGHTS_WITH_CAMERA
            observation = camera_w * max(0, yolo_count) + co2_w * co2_estimate + wifi_w * wifi_estimate
            measurement_variance = self.measurement_variance
        else:
            co2_w, wifi_w = WEIGHTS_WITHOUT_CAMERA
            observation = co2_w * co2_estimate + wifi_w * wifi_estimate
            measurement_variance = self.measurement_variance * NO_CAMERA_VARIANCE_FACTOR
        predicted_variance = self.variance + self.process_variance
        gain = predicted_variance / (predicted_variance + measurement_variance)
        self.estimate += gain * (observation - self.estimate)
        self.variance = (1 - gain) * predicted_variance
        return max(0, round(self.estimate)), internal_confidence(self.variance)


def internal_confidence(variance: float) -> float:
    """Estabilidad del filtro en 0–100 a partir de su varianza; no es una probabilidad calibrada."""
    return round(max(0.0, min(100.0, (1 - variance / 5) * 100)), 1)


def desk_state(people: int, objects: int, unattended_seconds: int,
               max_unattended_seconds: int = 900) -> str:
    for name, value in (("people", people), ("objects", objects),
                        ("unattended_seconds", unattended_seconds),
                        ("max_unattended_seconds", max_unattended_seconds)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} debe ser un entero no negativo")
    if max_unattended_seconds == 0:
        raise ValueError("max_unattended_seconds debe ser positivo")
    if people > 0:
        return "OCCUPIED_VERIFIED"
    if objects > 0 and unattended_seconds < max_unattended_seconds:
        return "POSSIBLE_ABANDONMENT"
    if objects > 0:
        return "RELEASE_RECOMMENDED"
    return "AVAILABLE"
