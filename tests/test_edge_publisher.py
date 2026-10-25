from datetime import datetime, timezone

import numpy as np

from edge import homografia
from edge.agente_pc import segundos_hasta
from edge.yolo_edge_publisher import mobiliario_en_piso, personas_en_piso

IDENTIDAD = homografia.calcular(homografia.ESQUINAS_PISO, homografia.ESQUINAS_PISO)


def test_people_are_placed_by_where_they_stand_and_weak_detections_are_dropped():
    cajas = [[0.45, 0.05, 0.55, 0.20], [0.10, 0.60, 0.20, 0.90], [0.70, 0.70, 0.80, 0.80], [0.3, 0.3, 0.4, 0.4]]
    clases = [0, 0, 0, 56]
    confianzas = [0.9, 0.8, 0.3, 0.9]
    personas = personas_en_piso(cajas, clases, confianzas, [1, 2, 3, 4], IDENTIDAD, confianza_minima=0.5)
    assert personas == [(1, 0.5, 0.2, 0.9), (2, 0.15, 0.9, 0.8)]


def test_furniture_is_placed_by_the_center_of_its_box():
    objetos = mobiliario_en_piso([[0.1, 0.4, 0.2, 0.5], [0.0, 0.0, 0.1, 0.1]], [62, 0], IDENTIDAD)
    assert [(o.clase, round(o.x, 2), round(o.y, 2)) for o in objetos] == [("monitor", 0.15, 0.45)]


def test_the_agent_knows_how_long_until_its_slot():
    ahora = datetime(2026, 10, 24, 13, 0, 0, tzinfo=timezone.utc)
    assert segundos_hasta("2026-10-24T13:00:20Z", ahora) == 20
    assert segundos_hasta(None, ahora) is None
    assert np.isclose(segundos_hasta("2026-10-24T12:59:59.500Z", ahora), -0.5)
