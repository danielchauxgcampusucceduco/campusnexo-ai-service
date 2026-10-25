from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from app.api.app_factory import create_app
from app.domain.pronostico import pronosticar

BOGOTA = timezone(timedelta(hours=-5))


def tres_semanas_de_clase():
    """Cada día hábil: clase de 24 personas de 8 a 10 (hora de Bogotá); el resto, vacío. Una muestra cada 15 min."""
    historial = []
    inicio = datetime(2026, 9, 28, 0, 0, tzinfo=BOGOTA)  # lunes
    for minuto in range(0, 21 * 24 * 60, 15):
        instante = inicio + timedelta(minutes=minuto)
        en_clase = instante.weekday() < 5 and 8 <= instante.hour < 10
        historial.append((instante, 24 if en_clase else 0))
    return historial


def test_the_forecast_follows_the_weekly_timetable():
    pronostico = pronosticar(tres_semanas_de_clase(), 30, 24, "America/Bogota")
    assert len(pronostico.puntos) == 24
    por_hora = {p.timestamp.astimezone(BOGOTA).hour: p for p in pronostico.puntos}
    assert por_hora[9].people == pytest.approx(24)
    assert por_hora[14].people == pytest.approx(0)
    assert all(0 <= p.low <= p.people <= p.high <= 30 for p in pronostico.puntos)


def test_recent_weeks_weigh_more():
    historial = tres_semanas_de_clase()
    ultima_semana = historial[-7 * 24 * 4:]
    cambiado = historial[:-7 * 24 * 4] + [(t, 12 if p else 0) for t, p in ultima_semana]
    por_hora = {p.timestamp.astimezone(BOGOTA).hour: p for p in pronosticar(cambiado, 30, 24, "America/Bogota").puntos}
    assert 12 < por_hora[9].people < 18, "la última semana pesa más que las anteriores"


def test_without_history_or_with_an_unknown_zone_it_refuses():
    with pytest.raises(ValueError):
        pronosticar([], 30, 12, "America/Bogota")
    client = TestClient(create_app(api_key=""))
    sample = {"timestamp": "2026-10-24T13:00:00Z", "people": 10}
    body = {"space_id": "301-A", "capacity": 30, "horizon_hours": 6, "history": [sample]}
    assert client.post("/v1/occupancy/forecast", json=dict(body, timezone="Marte/Olympus")).status_code == 422
    ok = client.post("/v1/occupancy/forecast", json=body)
    assert ok.status_code == 200
    assert ok.json()["space_id"] == "301-A"
    assert len(ok.json()["points"]) == 6
