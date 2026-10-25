import json

from entrenamiento import escena_sintetica as escena
from entrenamiento import ajustar_parametros, compuerta_calidad

UMBRALES = json.loads(compuerta_calidad.UMBRALES.read_text(encoding="utf-8"))


def test_the_gate_only_judges_what_was_measured():
    resultado = compuerta_calidad.evaluar({"mae_conteo": 0.8, "tasa_docente": 0.97}, UMBRALES)
    assert [(m, cumple) for m, _, _, cumple in resultado] == [("mae_conteo", True), ("tasa_docente", True)]
    assert not compuerta_calidad.evaluar({"recall_persona": 0.9}, UMBRALES)[0][3]


def test_the_gate_exit_code_blocks_a_worse_model(tmp_path):
    peor = tmp_path / "metricas.json"
    peor.write_text(json.dumps({"mae_conteo": 2.5}), encoding="utf-8")
    assert compuerta_calidad.main([str(peor)]) == 1
    mejor = tmp_path / "mejor.json"
    mejor.write_text(json.dumps({"mae_conteo": 0.5, "inferencia_ms": 120}), encoding="utf-8")
    assert compuerta_calidad.main([str(mejor)]) == 0


def test_tuning_filters_false_people_without_losing_the_teacher():
    muestras = ajustar_parametros.escenas(1500, escena.Ruido(0.05, 0.01, 0.3), semilla=3)
    sin_filtro = ajustar_parametros.medir(muestras, 0.0)
    resultado = ajustar_parametros.ajustar(muestras, UMBRALES)
    assert resultado["aprobado"]
    assert resultado["camera_variance"] < sin_filtro["camera_variance"], "el umbral elegido quita las personas falsas"
    assert resultado["tasa_docente"] >= UMBRALES["tasa_docente_min"]
    assert resultado["confianza_minima"] == 0.5, "el más bajo que deja fuera las falsas sin perder reales"


def test_the_tuning_is_reproducible(tmp_path):
    salida = tmp_path / "parametros.json"
    ajustar_parametros.main(["--escenas", "300", "--salida", str(salida)])
    primero = json.loads(salida.read_text(encoding="utf-8"))
    ajustar_parametros.main(["--escenas", "300", "--salida", str(salida)])
    assert json.loads(salida.read_text(encoding="utf-8")) == primero
