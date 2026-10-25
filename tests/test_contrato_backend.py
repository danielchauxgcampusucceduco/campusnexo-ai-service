"""El backend Java llama estas rutas (HttpOccupancyEstimatorAdapter y HttpAiAdvisorAdapter): si una cambia de
nombre o de método aquí, la prueba falla antes de que el backend caiga al respaldo en producción."""
import json

from scripts.exportar_openapi import contrato, main

RUTAS_DEL_BACKEND = {
    "/v1/occupancy/estimate": "post",
    "/v1/rooms/assignment": "post",
    "/v1/sensors/anomalies": "post",
    "/v1/occupancy/forecast": "post",
}


def test_las_rutas_del_backend_existen_con_su_metodo():
    rutas = contrato()["paths"]
    faltan = [f"{m.upper()} {r}" for r, m in RUTAS_DEL_BACKEND.items() if m not in rutas.get(r, {})]
    assert faltan == []


def test_exporta_el_contrato_como_json(tmp_path):
    salida = tmp_path / "openapi.json"
    assert main(["--salida", str(salida)]) == 0
    esquema = json.loads(salida.read_text(encoding="utf-8"))
    assert esquema["info"]["version"] == "0.4.0"
    assert set(RUTAS_DEL_BACKEND) <= set(esquema["paths"])
