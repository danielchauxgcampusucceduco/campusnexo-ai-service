"""Mensajes del borde al backend y el cliente HTTPS que los envía (solo biblioteca estándar).

Los mensajes de la cámara real (``yolo_edge_publisher.py``) llevan ``emulado=False``; una fuente de prueba local
los marca con ``emulado=True`` y el tablero lo muestra. Ninguna imagen sale del salón: solo posiciones en el piso y conteos.
"""
from __future__ import annotations

from datetime import datetime
import json
import urllib.error
import urllib.request

# Medio ancho y medio alto de la caja que representa a una persona alrededor de su punto en el piso.
MEDIA_CAJA = (0.02, 0.04)


def _caja(x: float, y: float) -> list[float]:
    dx, dy = MEDIA_CAJA
    return [round(max(0.0, x - dx), 4), round(max(0.0, y - dy), 4), round(min(1.0, x + dx), 4), round(min(1.0, y + dy), 4)]


def frame_camara(space_id: str, instante: datetime, personas: list[tuple[int, float, float, float]],
                 sensores: dict, emulado: bool, camara_en_linea: bool = True) -> dict:
    """Frame para ``POST /api/v1/twin/telemetry``. ``personas``: (track_id, x, y, confianza) en el piso."""
    return {
        "space_id": space_id,
        "timestamp": instante.isoformat(timespec="seconds"),
        "camera_online": camara_en_linea,
        "emulated": emulado,
        "detections": [{"track_id": track, "class": "person", "confidence": round(confianza, 3), "bbox": _caja(x, y)}
                       for track, x, y, confianza in personas] if camara_en_linea else [],
        "sensors": sensores,
    }


def lectura_ambiente(space_id: str, instante: datetime, temperatura_c: float, humedad_pct: float, co2_ppm: float,
                     lux: float, luces: bool, equipos: int) -> dict:
    """Lectura tipo Arduino para ``POST /api/v1/twin/environment``."""
    return {"space_id": space_id, "timestamp": instante.isoformat(timespec="seconds"), "temperature_c": temperatura_c,
            "humidity_pct": humedad_pct, "co2_ppm": co2_ppm, "illuminance_lux": lux, "lights_on": luces,
            "devices_on": equipos}


def descubrimiento(space_id: str, puestos, emulado: bool) -> dict:
    """Propuesta para ``POST /api/v1/workstations/discovery`` a partir de puestos vistos (``mobiliario.PuestoVisto``)."""
    return {"spaceId": space_id, "emulado": emulado,
            "puestos": [{"fila": p.fila, "columna": p.columna, "monitor": p.monitor, "silla": p.silla, "mesa": p.mesa}
                        for p in puestos]}


def auditoria(space_id: str, puestos, columnas: int) -> dict:
    """Mobiliario visto por puesto para ``POST /api/v1/workstations/audit``; el código es el del backend (P07)."""
    return {"spaceId": space_id,
            "puestos": [{"zoneId": f"{space_id}-P{(p.fila - 1) * columnas + p.columna:02d}", "silla": p.silla,
                         "mesa": p.mesa} for p in puestos]}


class Backend:
    """Cliente mínimo con la clave de sensor (``X-API-Key``). Las respuestas de error se devuelven, no se lanzan."""

    def __init__(self, url: str, clave: str, espera_s: float = 10.0):
        self.url = url.rstrip("/")
        self.clave = clave
        self.espera_s = espera_s

    def post(self, ruta: str, cuerpo: dict) -> tuple[int, dict | list | None]:
        solicitud = urllib.request.Request(self.url + ruta, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
                                           headers={"Content-Type": "application/json", "X-API-Key": self.clave})
        try:
            with urllib.request.urlopen(solicitud, timeout=self.espera_s) as respuesta:
                texto = respuesta.read().decode("utf-8")
                return respuesta.status, json.loads(texto) if texto else None
        except urllib.error.HTTPError as error:
            texto = error.read().decode("utf-8", errors="replace")
            try:
                return error.code, json.loads(texto) if texto else None
            except json.JSONDecodeError:
                return error.code, {"detail": texto}
