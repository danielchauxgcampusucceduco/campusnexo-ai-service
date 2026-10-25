from types import SimpleNamespace

from carga.prueba_carga import frame, resumen
from entrenamiento.entrenar import metricas_de


def test_the_load_summary_checks_the_scalability_attribute():
    rapido = resumen([20.0] * 95 + [250.0] * 5, errores=0, total=100)
    assert rapido["p95_ms"] < 300 and rapido["cumple_qa3"]
    lento = resumen([20.0] * 90 + [800.0] * 10, errores=0, total=100)
    assert not lento["cumple_qa3"]
    assert not resumen([20.0] * 100, errores=5, total=100)["cumple_qa3"], "más de 1 % de errores no cumple"


def test_load_frames_are_marked_as_emulated():
    cuerpo = frame("301-A", 3)
    assert cuerpo["emulated"] is True and len(cuerpo["detections"]) == 3


def test_yolo_metrics_are_read_for_the_person_class():
    validacion = SimpleNamespace(box=SimpleNamespace(r=[0.96, 0.5], p=[0.91, 0.4], map50=0.88),
                                 speed={"inference": 143.27})
    assert metricas_de(validacion) == {"recall_persona": 0.96, "precision_persona": 0.91, "map50": 0.88,
                                       "inferencia_ms": 143.3}
