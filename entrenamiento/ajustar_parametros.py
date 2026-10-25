#!/usr/bin/env python3
"""Ajuste de parámetros sin hardware: aprende de escenas sintéticas cuánto confiar en el detector.

Un detector real pierde personas y a veces "ve" una que no existe, casi siempre con baja confianza. Sobre miles de
escenas sintéticas con ese ruido (salones con docente adelante y estudiantes al fondo, de vacíos a llenos), prueba
cada umbral de confianza mínima y mide contra la verdad de terreno:

* el error medio absoluto del conteo de la cámara (``mae_conteo``);
* la fracción de escenas con docente en las que el docente sigue detectado en su zona (``tasa_docente``).

Entre los umbrales que cumplen la compuerta elige el de **menor varianza del error**, no el de menor MAE: una persona
falsa compensa a una perdida y hace ver mejor el MAE, pero en un salón vacío es ocupación fantasma (las luces no se
apagan). La varianza es además lo que el filtro de Kalman del backend supone del ruido de la cámara
(``KALMAN_CAMERA_VARIANCE``). En empate gana el umbral más bajo, lejos del punto donde empieza a perder personas
reales. Escribe ``parametros.json``; el publicador de borde lee de ahí su confianza mínima.

    python -m entrenamiento.ajustar_parametros --escenas 4000
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

import numpy as np

from entrenamiento import escena_sintetica as escena
from entrenamiento.compuerta_calidad import UMBRALES, evaluar

CANDIDATOS = (0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7)
SALAS = (escena.Salon("301-A", 5, 6, 60.0, 30), escena.Salon("303-A", 6, 6, 54.0, 36))
SALIDA = Path(__file__).with_name("parametros.json")


def escenas(n: int, ruido: escena.Ruido, semilla: int) -> list[tuple[int, int, list[escena.Persona]]]:
    """(personas reales, docentes, detecciones) de ``n`` escenas al azar, siempre las mismas para una semilla."""
    rng = random.Random(semilla)
    resultado = []
    for _ in range(n):
        salon = rng.choice(SALAS)
        docentes = rng.choice((0, 1))
        estudiantes = rng.randint(0, salon.capacidad)
        de_pie = rng.choice((0, 0, 0, 1, 2))
        resultado.append((docentes + estudiantes + de_pie, docentes,
                          escena.personas(salon, docentes, estudiantes, de_pie, ruido, rng)))
    return resultado


def medir(muestras, confianza_minima: float) -> dict:
    errores, con_docente, docente_visto, vacios, fantasmas = [], 0, 0, 0, 0
    for reales, docentes, detecciones in muestras:
        vistas = [d for d in detecciones if d.confianza >= confianza_minima]
        errores.append(len(vistas) - reales)
        if reales == 0:
            vacios += 1
            fantasmas += bool(vistas)
        if docentes:
            con_docente += 1
            docente_visto += any(d.docente and d.y < escena.ARRIBA for d in vistas)
    errores = np.array(errores, dtype=float)
    return {"confianza_minima": confianza_minima, "mae_conteo": round(float(np.mean(np.abs(errores))), 4),
            "sesgo": round(float(np.mean(errores)), 4), "camera_variance": round(float(np.var(errores)), 4),
            "tasa_docente": round(docente_visto / con_docente, 4) if con_docente else 1.0,
            "ocupacion_fantasma": round(fantasmas / vacios, 4) if vacios else 0.0}


def ajustar(muestras, umbrales: dict) -> dict:
    """El umbral de menor varianza del error entre los que pasan la compuerta; si ninguno pasa, el mejor, marcado."""
    medidas = [medir(muestras, c) for c in CANDIDATOS]
    aprobadas = [m for m in medidas if all(cumple for *_, cumple in evaluar(
        {"mae_conteo": m["mae_conteo"], "tasa_docente": m["tasa_docente"]}, umbrales))]
    elegida = min(aprobadas or medidas, key=lambda m: (m["camera_variance"], m["mae_conteo"], m["confianza_minima"]))
    return {**elegida, "aprobado": bool(aprobadas), "candidatos": medidas}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--escenas", type=int, default=4000)
    parser.add_argument("--perdida", type=float, default=0.05)
    parser.add_argument("--desplazamiento", type=float, default=0.01)
    parser.add_argument("--falsos", type=float, default=0.05)
    parser.add_argument("--semilla", type=int, default=7)
    parser.add_argument("--salida", default=str(SALIDA))
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa otra página de códigos
    ruido = escena.Ruido(args.perdida, args.desplazamiento, args.falsos)
    umbrales = json.loads(UMBRALES.read_text(encoding="utf-8"))
    resultado = ajustar(escenas(args.escenas, ruido, args.semilla), umbrales)
    resultado.update({"origen": "escenas_sinteticas", "escenas": args.escenas, "ruido": ruido.__dict__})
    Path(args.salida).write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"confianza mínima {resultado['confianza_minima']}: MAE {resultado['mae_conteo']}, "
          f"docente {resultado['tasa_docente']:.1%} → {'APROBADO' if resultado['aprobado'] else 'RECHAZADO'}")
    print(f"KALMAN_CAMERA_VARIANCE={max(resultado['camera_variance'], 0.25)}")
    return 0 if resultado["aprobado"] else 1


if __name__ == "__main__":
    sys.exit(main())
