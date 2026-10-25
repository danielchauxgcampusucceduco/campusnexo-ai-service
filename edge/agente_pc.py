#!/usr/bin/env python3
"""Agente de latido de cada computador de una sala (solo biblioteca estándar).

Cada minuto envía ``POST /api/v1/workstations/heartbeats`` con el nombre del equipo y el salón donde se instaló.
Así el backend sabe qué computadores siguen encendidos (la cámara no ve las torres bajo las mesas). Si el
computador todavía no está en un puesto y hay un emparejamiento programado, la respuesta trae su ranura: en ese
momento el agente muestra unos segundos un patrón a pantalla completa para que la cámara vea en qué puesto está.

    python agente_pc.py --space-id 301-A --backend https://campusnexo-backend.onrender.com

La clave de sensor se lee de la variable de entorno ``CAMPUSNEXO_SENSOR_KEY``; nunca va en la línea de comandos.
Instalación sugerida en Windows: una tarea programada "al iniciar sesión" que ejecute este archivo con pythonw.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import socket
import time

try:
    from edge.contrato import Backend
except ImportError:  # copiado solo en el PC: el cliente es pequeño, se repite aquí
    from contrato import Backend  # type: ignore[no-redef]

INTERVALO_S = 60


def segundos_hasta(instante_iso: str | None, ahora: datetime) -> float | None:
    """Segundos hasta el inicio de la ranura, o None si no hay ranura."""
    if not instante_iso:
        return None
    return (datetime.fromisoformat(instante_iso.replace("Z", "+00:00")) - ahora).total_seconds()


def mostrar_patron(segundos: float) -> None:
    """Pantalla completa alternando blanco y negro: un cambio de brillo que la cámara distingue de cualquier uso."""
    import tkinter

    ventana = tkinter.Tk()
    ventana.attributes("-fullscreen", True)
    ventana.attributes("-topmost", True)
    colores, fin = ("#FFFFFF", "#000000"), time.monotonic() + segundos
    paso = 0
    while time.monotonic() < fin:
        ventana.configure(background=colores[paso % 2])
        ventana.update()
        time.sleep(0.5)
        paso += 1
    ventana.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--space-id", required=True, help="salón donde está instalado el computador")
    parser.add_argument("--backend", default=os.environ.get("CAMPUSNEXO_BACKEND_URL", "http://localhost:8080"))
    parser.add_argument("--cpu", default=socket.gethostname(), help="código del computador (nombre del equipo)")
    args = parser.parse_args()
    backend = Backend(args.backend, os.environ.get("CAMPUSNEXO_SENSOR_KEY", ""))
    while True:
        try:
            estado, respuesta = backend.post("/api/v1/workstations/heartbeats",
                                             {"cpu": args.cpu, "spaceId": args.space_id})
        except OSError as error:  # red caída: se reintenta en el próximo latido
            estado, respuesta = None, {"detail": str(error)}
        espera = INTERVALO_S
        if estado == 202 and respuesta and not respuesta.get("asignado"):
            faltan = segundos_hasta(respuesta.get("patronDesde"), datetime.now(timezone.utc))
            duracion = segundos_hasta(respuesta.get("patronHasta"), datetime.now(timezone.utc))
            if faltan is not None and duracion is not None and faltan < INTERVALO_S:
                time.sleep(max(0.0, faltan))
                mostrar_patron(max(0.5, duracion - max(0.0, faltan)))
                espera = max(1, INTERVALO_S - duracion)
        time.sleep(espera)


if __name__ == "__main__":
    main()
