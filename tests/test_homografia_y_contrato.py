from datetime import datetime, timezone
import json

import numpy as np
import pytest

from app.domain.mobiliario import PuestoVisto
from edge import contrato, homografia

# La cámara en la esquina trasera derecha ve el piso como un trapecio: el tablero (adelante) queda lejos y arriba.
ESQUINAS_IMAGEN = [[0.30, 0.20], [0.70, 0.22], [0.98, 0.95], [0.05, 0.90]]


def test_the_corners_of_the_image_land_on_the_corners_of_the_floor():
    matriz = homografia.calcular(ESQUINAS_IMAGEN, homografia.ESQUINAS_PISO)
    np.testing.assert_allclose(homografia.aplicar(matriz, ESQUINAS_IMAGEN), homografia.ESQUINAS_PISO, atol=1e-9)
    centro = homografia.aplicar(matriz, [[0.5, 0.5]])[0]
    assert 0 < centro[0] < 1 and 0 < centro[1] < 1


def test_aligned_corners_are_refused(tmp_path):
    with pytest.raises(ValueError, match="alineadas"):
        homografia.calcular([[0, 0], [0.5, 0.5], [1, 1], [0.2, 0.2]], homografia.ESQUINAS_PISO)
    archivo = tmp_path / "calibracion-301A.json"
    archivo.write_text(json.dumps({"space_id": "301-A", "esquinas_imagen": ESQUINAS_IMAGEN}), encoding="utf-8")
    space_id, matriz = homografia.cargar(archivo)
    assert space_id == "301-A" and matriz.shape == (3, 3)


def test_messages_match_the_backend_contracts():
    instante = datetime(2026, 10, 24, 13, 0, tzinfo=timezone.utc)
    frame = contrato.frame_camara("303-A", instante, [(1, 0.5, 0.15, 0.91)], {"co2_ppm": 600}, emulado=True)
    assert frame["emulated"] is True
    assert frame["detections"][0]["bbox"] == [0.48, 0.11, 0.52, 0.19]
    assert contrato.frame_camara("303-A", instante, [(1, 0.5, 0.5, 0.9)], {}, True, camara_en_linea=False)[
        "detections"] == []
    puestos = [PuestoVisto(2, 1, 0.1, 0.5, True, False, True)]
    assert contrato.descubrimiento("301-A", puestos, True)["puestos"][0] == {
        "fila": 2, "columna": 1, "monitor": True, "silla": False, "mesa": True}
    assert contrato.auditoria("301-A", puestos, columnas=6)["puestos"][0]["zoneId"] == "301-A-P07"
