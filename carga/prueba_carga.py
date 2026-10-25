#!/usr/bin/env python3
"""Prueba de carga de la ingesta del gemelo (atributo de calidad QA-3: escalabilidad).

Envía frames de cámara de ``--salones`` salones a ``--hz`` por segundo durante ``--segundos`` y mide la latencia de
``POST /api/v1/twin/telemetry`` (p50, p95, p99) y la tasa de error. Son peticiones de prueba marcadas
``emulated: true``: córrela solo contra el entorno local de ``docker compose``, nunca contra la base de producción.

    python -m carga.prueba_carga --backend http://localhost:8080 --salones 107 --hz 1 --segundos 60
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import sys
import time

import numpy as np

QA3_P95_MS = 300
QA3_ERROR_MAX = 0.01


def frame(space_id: str, numero: int) -> dict:
    return {"space_id": space_id, "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "camera_online": True, "emulated": True,
            "detections": [{"track_id": i, "class": "person", "confidence": 0.9,
                            "bbox": [0.1 + 0.02 * i, 0.5, 0.12 + 0.02 * i, 0.58]} for i in range(numero % 20)],
            "sensors": {"co2_ppm": 600, "temperature_c": 18.0, "humidity_pct": 55}}


def resumen(latencias_ms: list[float], errores: int, total: int) -> dict:
    if not latencias_ms:
        return {"peticiones": total, "error": 1.0}
    p50, p95, p99 = np.percentile(latencias_ms, [50, 95, 99])
    tasa = errores / total if total else 0.0
    return {"peticiones": total, "p50_ms": round(float(p50), 1), "p95_ms": round(float(p95), 1),
            "p99_ms": round(float(p99), 1), "error": round(tasa, 4),
            "cumple_qa3": bool(p95 < QA3_P95_MS and tasa < QA3_ERROR_MAX)}


async def correr(backend: str, clave: str, salones: list[str], hz: float, segundos: float) -> dict:
    import httpx  # dependencia opcional: extra "carga"

    latencias, errores, total = [], 0, 0
    async with httpx.AsyncClient(base_url=backend, headers={"X-API-Key": clave}, timeout=10) as cliente:
        async def enviar(space_id: str, numero: int):
            nonlocal errores, total
            inicio = time.perf_counter()
            try:
                respuesta = await cliente.post("/api/v1/twin/telemetry", json=frame(space_id, numero))
                if respuesta.status_code >= 400:
                    errores += 1
            except httpx.HTTPError:
                errores += 1
            latencias.append((time.perf_counter() - inicio) * 1000)
            total += 1

        fin, numero = time.monotonic() + segundos, 0
        while time.monotonic() < fin:
            ronda = time.monotonic()
            await asyncio.gather(*(enviar(space_id, numero) for space_id in salones))
            numero += 1
            await asyncio.sleep(max(0.0, 1 / hz - (time.monotonic() - ronda)))
    return resumen(latencias, errores, total)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", default="http://localhost:8080")
    parser.add_argument("--salones", type=int, default=107)
    parser.add_argument("--hz", type=float, default=1.0)
    parser.add_argument("--segundos", type=float, default=60)
    parser.add_argument("--catalogo", default="salones.txt", help="códigos de salón, uno por línea (del catálogo)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    with open(args.catalogo, encoding="utf-8") as archivo:
        salones = [linea.strip() for linea in archivo if linea.strip()][:args.salones]
    resultado = asyncio.run(correr(args.backend, os.environ.get("CAMPUSNEXO_SENSOR_KEY", ""), salones, args.hz,
                                   args.segundos))
    print(json.dumps(resultado, indent=2))
    return 0 if resultado.get("cumple_qa3") else 1


if __name__ == "__main__":
    sys.exit(main())
