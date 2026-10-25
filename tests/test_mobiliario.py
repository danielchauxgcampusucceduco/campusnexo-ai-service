import numpy as np

from app.domain.mobiliario import Objeto, auditar, consolidar, descubrir, patron_visto


def sala(filas=5, columnas=6, sin_silla=()):
    """Mobiliario de una sala de cómputo vista desde arriba: monitor, mesa y silla por puesto."""
    objetos = []
    for f in range(filas):
        for c in range(columnas):
            x, y = 0.1 + c * 0.15, 0.35 + f * 0.12
            objetos += [Objeto("monitor", x, y), Objeto("mesa", x, y + 0.02)]
            if (f + 1, c + 1) not in sin_silla:
                objetos.append(Objeto("silla", x, y + 0.06))
    return objetos


def test_discovers_rows_and_columns_from_the_monitors():
    puestos = descubrir(sala())
    assert len(puestos) == 30
    assert [p.etiqueta for p in puestos[:7]] == ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    assert puestos[-1].etiqueta == "E6"
    assert all(p.monitor and p.silla and p.mesa for p in puestos)


def test_a_seat_without_chair_is_proposed_anyway():
    puestos = {p.etiqueta: p for p in descubrir(sala(sin_silla={(1, 4)}))}
    assert not puestos["A4"].silla
    assert puestos["A4"].mesa
    assert puestos["A5"].silla, "la silla de A5 no se presta a A4"


def test_only_objects_seen_in_most_frames_count():
    estable = Objeto("monitor", 0.5, 0.5)
    frames = [[estable, Objeto("silla", 0.9, 0.9)], [Objeto("monitor", 0.51, 0.5)], [Objeto("monitor", 0.5, 0.51)]]
    consolidados = consolidar(frames)
    assert len(consolidados) == 1
    assert consolidados[0].clase == "monitor"
    assert abs(consolidados[0].x - 0.503) < 0.001


def test_the_audit_sees_which_chair_is_missing_now():
    conocidos = descubrir(sala())
    ahora = auditar(conocidos, sala(sin_silla={(2, 3)}))
    faltan = [p.etiqueta for p in ahora if not p.silla]
    assert faltan == ["B3"]


def test_the_monitor_that_shows_the_pattern_is_found():
    antes = np.full((100, 300), 30, dtype=np.uint8)
    despues = antes.copy()
    despues[10:40, 110:190] = 230
    regiones = [(10, 10, 90, 40), (110, 10, 190, 40), (210, 10, 290, 40)]
    assert patron_visto(antes, despues, regiones) == 1
    assert patron_visto(antes, antes, regiones) is None
    alguien_pasa = antes.copy()
    alguien_pasa[10:40, 10:290] = 120
    assert patron_visto(antes, alguien_pasa, regiones) is None, "si todo cambia igual no es un patrón"
