#!/usr/bin/env python3
"""Cámara de un salón en el dispositivo de borde.

YOLO + ByteTrack sobre la cámara (o un video) del salón. Cada persona se proyecta al piso con la homografía de la
calibración (``calibrar.py``) y al backend solo viaja su posición: **ningún frame sale del dispositivo ni se graba**.

Modos:

* publicar (por defecto): un frame por intervalo a ``POST /api/v1/twin/telemetry`` por HTTPS (o MQTT con ``--mqtt``).
* ``--descubrir``: con el salón vacío, consolida varios frames de mobiliario y envía la propuesta de puestos; guarda
  los puestos vistos en ``puestos-<salón>.json`` para auditar y emparejar después.
* ``--auditar``: compara la silla y la mesa que se ven ahora en cada puesto con lo que el inventario espera.
* ``--emparejar``: mientras el administrador empareja, vigila el brillo de cada monitor y reporta en qué puesto
  apareció el patrón del computador de turno.

Ejemplo::

    python -m edge.yolo_edge_publisher --calibracion calibracion-301A.json --source 0 \\
        --backend https://campusnexo-backend.onrender.com --clave "$CAMPUSNEXO_SENSOR_KEY"
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from app.domain import mobiliario
from edge import contrato, homografia

PERSONA = 0
PARAMETROS = Path(__file__).resolve().parent.parent / "entrenamiento" / "parametros.json"


def confianza_por_defecto() -> float:
    """La que eligió el ajuste de parámetros (``entrenamiento/ajustar_parametros.py``), o 0,5."""
    try:
        return float(json.loads(PARAMETROS.read_text(encoding="utf-8"))["confianza_minima"])
    except (OSError, KeyError, ValueError):
        return 0.5


def _en_piso(matriz: np.ndarray, x: float, y: float) -> tuple[float, float]:
    px, py = homografia.aplicar(matriz, [[x, y]])[0]
    return min(1.0, max(0.0, float(px))), min(1.0, max(0.0, float(py)))


def personas_en_piso(cajas, clases, confianzas, tracks, matriz: np.ndarray,
                     confianza_minima: float) -> list[tuple[int, float, float, float]]:
    """(track, x, y, confianza) en el piso de cada persona: el punto de apoyo es el centro del borde inferior de su caja."""
    personas = []
    for (x0, _y0, x1, y1), clase, confianza, track in zip(cajas, clases, confianzas, tracks):
        if int(clase) != PERSONA or confianza < confianza_minima:
            continue
        x, y = _en_piso(matriz, (x0 + x1) / 2, y1)
        personas.append((int(track), round(x, 4), round(y, 4), float(confianza)))
    return personas


def mobiliario_en_piso(cajas, clases, matriz: np.ndarray) -> list[mobiliario.Objeto]:
    """Monitores, sillas, mesas y portátiles en el piso, por el centro de su caja."""
    objetos = []
    for (x0, y0, x1, y1), clase in zip(cajas, clases):
        nombre = mobiliario.COCO_MOBILIARIO.get(int(clase))
        if nombre:
            x, y = _en_piso(matriz, (x0 + x1) / 2, (y0 + y1) / 2)
            objetos.append(mobiliario.Objeto(nombre, x, y))
    return objetos


def _resultados(args):
    from ultralytics import YOLO  # dependencia opcional: extra "vision"

    modelo = YOLO(args.model)
    fuente = int(args.source) if args.source.isdigit() else args.source
    clases = [PERSONA, *mobiliario.COCO_MOBILIARIO]
    yield from modelo.track(source=fuente, stream=True, persist=True, tracker="bytetrack.yaml", classes=clases,
                            verbose=False)


def _arreglos(resultado):
    cajas = resultado.boxes
    if cajas is None or len(cajas) == 0:
        return [], [], [], []
    tracks = cajas.id.tolist() if cajas.id is not None else [0] * len(cajas)
    return cajas.xyxyn.tolist(), cajas.cls.tolist(), cajas.conf.tolist(), tracks


def _archivo_puestos(space_id: str) -> Path:
    return Path(f"puestos-{space_id}.json")


def publicar(args, space_id, matriz, backend, enviar_mqtt):
    sensores = {"co2_ppm": args.co2, "temperature_c": args.temperature, "humidity_pct": args.humidity,
                "illuminance_lux": args.lux, "wifi_devices": args.wifi, "active_power_kw": args.power}
    ultimo = 0.0
    for resultado in _resultados(args):
        if time.monotonic() - ultimo < args.intervalo:
            continue
        cajas, clases, confianzas, tracks = _arreglos(resultado)
        personas = personas_en_piso(cajas, clases, confianzas, tracks, matriz, args.confianza_minima)
        frame = contrato.frame_camara(space_id, datetime.now(timezone.utc), personas, sensores, emulado=False)
        if enviar_mqtt:
            enviar_mqtt(frame)
        else:
            estado, _ = backend.post("/api/v1/twin/telemetry", frame)
            print(f"{frame['timestamp']} {space_id}: {len(personas)} personas → HTTP {estado}")
        ultimo = time.monotonic()


def _mobiliario_estable(args, matriz) -> list[mobiliario.Objeto]:
    frames = []
    for resultado in _resultados(args):
        cajas, clases, _, _ = _arreglos(resultado)
        frames.append(mobiliario_en_piso(cajas, clases, matriz))
        if len(frames) >= args.frames:
            break
    return mobiliario.consolidar(frames)


def descubrir(args, space_id, matriz, backend):
    puestos = mobiliario.descubrir(_mobiliario_estable(args, matriz))
    _archivo_puestos(space_id).write_text(json.dumps([p.__dict__ for p in puestos], indent=1), encoding="utf-8")
    estado, respuesta = backend.post("/api/v1/workstations/discovery", contrato.descubrimiento(space_id, puestos, False))
    print(f"{len(puestos)} puestos propuestos, {sum(not (p.silla and p.mesa) for p in puestos)} incompletos "
          f"→ HTTP {estado} {respuesta or ''}")


def _puestos_guardados(space_id: str) -> list[mobiliario.PuestoVisto]:
    return [mobiliario.PuestoVisto(**datos) for datos in json.loads(_archivo_puestos(space_id).read_text(encoding="utf-8"))]


def auditar(args, space_id, matriz, backend):
    puestos = _puestos_guardados(space_id)
    vistos = mobiliario.auditar(puestos, _mobiliario_estable(args, matriz))
    columnas = max(p.columna for p in puestos)
    estado, hallazgos = backend.post("/api/v1/workstations/audit", contrato.auditoria(space_id, vistos, columnas))
    print(f"Auditoría → HTTP {estado}: {hallazgos}")


def emparejar(args, space_id, matriz, backend):
    """Vigila la región de cada monitor; el patrón de un computador cambia una sola región durante su ranura."""
    import cv2  # dependencia opcional: extra "vision"

    puestos = _puestos_guardados(space_id)
    inversa = np.linalg.inv(matriz)
    captura = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    ok, imagen = captura.read()
    if not ok:
        raise SystemExit("No se pudo leer la cámara")
    alto, ancho = imagen.shape[:2]
    regiones = []
    for puesto in puestos:
        x, y = homografia.aplicar(inversa, [[puesto.x, puesto.y]])[0]
        cx, cy, medio = int(x * ancho), int(y * alto), max(6, int(0.02 * ancho))
        regiones.append((max(0, cx - medio), max(0, cy - medio), min(ancho, cx + medio), min(alto, cy + medio)))
    referencia = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    reportado, fin = 0.0, time.monotonic() + args.duracion
    while time.monotonic() < fin:
        ok, imagen = captura.read()
        if not ok:
            break
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        indice = mobiliario.patron_visto(referencia, gris, regiones)
        if indice is not None and time.monotonic() - reportado > 2:
            puesto = puestos[indice]
            estado, _ = backend.post("/api/v1/workstations/pairing", {
                "spaceId": space_id, "fila": puesto.fila, "columna": puesto.columna,
                "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds")})
            print(f"Patrón en {puesto.etiqueta} → HTTP {estado}")
            reportado = time.monotonic()
        referencia = gris
    captura.release()


def _mqtt(args, space_id):
    import paho.mqtt.client as mqtt  # dependencia opcional: extra "edge"

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"edge-{space_id}")
    cliente.connect(args.mqtt, args.mqtt_port, keepalive=30)
    cliente.loop_start()
    bloque, piso = f"bloque_{space_id[-1].lower()}", f"piso_{space_id[0]}"
    topico = f"ucc/pasto/{bloque}/{piso}/{space_id}/camara"
    return lambda frame: cliente.publish(topico, json.dumps(frame), qos=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--calibracion", required=True, help="archivo de calibrar.py")
    parser.add_argument("--source", required=True, help="índice de cámara, URL RTSP o ruta de video")
    parser.add_argument("--backend", default=os.environ.get("CAMPUSNEXO_BACKEND_URL", "http://localhost:8080"))
    parser.add_argument("--clave", default=os.environ.get("CAMPUSNEXO_SENSOR_KEY", ""), help="clave de sensor")
    parser.add_argument("--model", default=os.environ.get("YOLO_MODEL", "yolo11n.pt"))
    parser.add_argument("--intervalo", type=float, default=2.0, help="segundos entre frames publicados")
    parser.add_argument("--confianza-minima", type=float, default=confianza_por_defecto())
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--descubrir", action="store_true")
    modo.add_argument("--auditar", action="store_true")
    modo.add_argument("--emparejar", action="store_true")
    parser.add_argument("--frames", type=int, default=10, help="frames del salón vacío al descubrir o auditar")
    parser.add_argument("--duracion", type=float, default=300, help="segundos vigilando el emparejamiento")
    parser.add_argument("--mqtt", help="broker MQTT en vez de HTTPS")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    # Valores del salón cuando no tiene Arduino: el contrato del frame los exige; el Arduino los reemplaza.
    parser.add_argument("--co2", type=float, default=420)
    parser.add_argument("--temperature", type=float, default=18.0)
    parser.add_argument("--humidity", type=float, default=55)
    parser.add_argument("--lux", type=float, default=0)
    parser.add_argument("--wifi", type=int, default=0)
    parser.add_argument("--power", type=float, default=0)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa otra página de códigos

    space_id, matriz = homografia.cargar(args.calibracion)
    backend = contrato.Backend(args.backend, args.clave)
    if args.descubrir:
        descubrir(args, space_id, matriz, backend)
    elif args.auditar:
        auditar(args, space_id, matriz, backend)
    elif args.emparejar:
        emparejar(args, space_id, matriz, backend)
    else:
        try:
            publicar(args, space_id, matriz, backend, _mqtt(args, space_id) if args.mqtt else None)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
