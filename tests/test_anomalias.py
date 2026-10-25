from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.app_factory import create_app
from app.domain.anomalias import LECTURAS_PEGADAS, Lectura, detectar

INICIO = datetime(2026, 10, 24, 13, 0, tzinfo=timezone.utc)


def serie(space_id="301-A", n=30, **sobrescribir):
    """Lecturas sanas de un minuto: CO₂ y temperatura oscilan un poco, como un sensor real."""
    lecturas = []
    for i in range(n):
        valores = {"co2_ppm": 600 + (i % 5) * 7.0, "temperature_c": 18 + (i % 3) * 0.1, "humidity_pct": 55 + (i % 4) * 0.5,
                   "illuminance_lux": 400.0, "active_power_kw": 1.5}
        for sensor, cambio in sobrescribir.items():
            valor = cambio(i)
            if valor is not None:
                valores[sensor] = valor
        lecturas.append(Lectura(space_id, INICIO + timedelta(minutes=i), valores))
    return lecturas


def tipos(anomalias):
    return [(a.sensor, a.tipo) for a in anomalias]


def test_a_healthy_room_has_no_anomalies_even_with_lights_off_for_hours():
    assert detectar(serie(illuminance_lux=lambda i: 0.0, active_power_kw=lambda i: 0.0)) == []


def test_impossible_values_are_out_of_range():
    anomalias = detectar(serie(humidity_pct=lambda i: 140.0 if i == 7 else None))
    assert ("humidity_pct", "FUERA_DE_RANGO") in tipos(anomalias)
    assert anomalias[0].timestamp == INICIO + timedelta(minutes=7)


def test_a_frozen_co2_sensor_is_reported_once_per_run():
    anomalias = [a for a in detectar(serie(co2_ppm=lambda i: 812.0 if i >= 5 else None)) if a.tipo == "VALOR_PEGADO"]
    assert len(anomalias) == 1
    assert anomalias[0].timestamp == INICIO + timedelta(minutes=5 + LECTURAS_PEGADAS - 1)


def test_a_sudden_jump_is_flagged_but_normal_noise_is_not():
    anomalias = detectar(serie(temperature_c=lambda i: 31.0 if i == 20 else None))
    assert ("temperature_c", "SALTO") in tipos(anomalias)
    assert all(a.space_id == "301-A" for a in anomalias)


def test_the_api_contract_matches_what_the_backend_sends():
    client = TestClient(create_app(api_key=""))
    readings = [{"space_id": l.space_id, "timestamp": l.timestamp.isoformat(), **l.valores}
                for l in serie(co2_ppm=lambda i: 9000.0 if i == 3 else None)]
    response = client.post("/v1/sensors/anomalies", json={"readings": readings})
    assert response.status_code == 200
    body = response.json()
    assert body["readings_analyzed"] == 30
    assert {"space_id": "301-A", "sensor": "co2_ppm", "kind": "FUERA_DE_RANGO"}.items() <= body["anomalies"][0].items()
    naive = dict(readings[0], timestamp="2026-10-24T13:00:00")
    assert client.post("/v1/sensors/anomalies", json={"readings": [naive]}).status_code == 422
