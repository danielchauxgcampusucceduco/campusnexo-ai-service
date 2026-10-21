"""Simulación 1R1C de primer orden; parámetros deben calibrarse en cada espacio."""
import math

def simulate_free_warming(current_temp_c: float, outside_temp_c: float, occupancy: int,
                          lighting_kw: float, resistance_c_per_kw: float = 2.4,
                          capacitance_kwh_per_c: float = 1.85,
                          comfort_limit_c: float = 24.5, max_minutes: int = 20) -> dict:
    if resistance_c_per_kw <= 0 or capacitance_kwh_per_c <= 0:
        raise ValueError("R y C deben ser positivos")
    if occupancy < 0 or lighting_kw < 0 or max_minutes < 0:
        raise ValueError("La ocupación, carga y duración no pueden ser negativas")
    # Modelo explícito Euler: C dT/dt = (Tout-T)/R + ganancias internas.
    # Se limita a 20 min para que la sugerencia no exceda el horizonte de esta demo.
    step_min = 1
    temp = current_temp_c
    rate_first = 0.0
    reached = 0 if current_temp_c >= comfort_limit_c else None
    for minute in range(1, min(max_minutes, 120) + 1):
        q_envelope = (outside_temp_c - temp) / resistance_c_per_kw
        q_internal = occupancy * 0.115 + lighting_kw
        delta = ((q_envelope + q_internal) / capacitance_kwh_per_c) * (step_min / 60)
        if minute == 1:
            rate_first = delta
        temp += delta
        if reached is None and temp >= comfort_limit_c:
            reached = minute
    return {
        "model": "1R1C_forward_euler",
        "safe_off_duration_min": min(max_minutes, reached) if reached is not None else max_minutes,
        "projected_temp_at_horizon_c": round(temp, 2),
        "initial_rate_c_per_min": round(rate_first, 4),
        "comfort_limit_c": comfort_limit_c,
        "note": "Estimación de demostración; requiere calibración local y no controla equipos.",
    }
