"""Proyección exponencial exacta del modelo térmico 1R1C; parámetros requieren calibración local."""
import math


def _require_range(name: str, value: float, minimum: float, maximum: float) -> None:
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} debe estar entre {minimum} y {maximum}")


def simulate_free_warming(current_temp_c: float, outside_temp_c: float, occupancy: int,
                          lighting_kw: float, resistance_c_per_kw: float = 2.4,
                          capacitance_kwh_per_c: float = 1.85,
                          comfort_limit_c: float = 24.5, max_minutes: int = 20) -> dict:
    for name, value in (("occupancy", occupancy), ("max_minutes", max_minutes)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} debe ser un entero")
    _require_range("current_temp_c", current_temp_c, -20, 60)
    _require_range("outside_temp_c", outside_temp_c, -30, 60)
    _require_range("occupancy", occupancy, 0, 1000)
    _require_range("lighting_kw", lighting_kw, 0, 100)
    _require_range("resistance_c_per_kw", resistance_c_per_kw, 1e-6, 1000)
    _require_range("capacitance_kwh_per_c", capacitance_kwh_per_c, 1e-6, 1000)
    _require_range("comfort_limit_c", comfort_limit_c, 10, 35)
    _require_range("max_minutes", max_minutes, 0, 120)

    # C dT/dt = (Tout-T)/R + q. With constant q, the exact solution is
    # T(t) = equilibrium + (T0-equilibrium)e^(-t/(R*C)).
    internal_gain_kw = occupancy * 0.115 + lighting_kw
    equilibrium_c = outside_temp_c + resistance_c_per_kw * internal_gain_kw
    minute_fraction = -math.expm1(-1 / (60 * resistance_c_per_kw * capacitance_kwh_per_c))
    temp = current_temp_c
    rate_first = 0.0
    reached = 0 if current_temp_c >= comfort_limit_c else None
    for minute in range(1, min(max_minutes, 120) + 1):
        delta = (equilibrium_c - temp) * minute_fraction
        if minute == 1:
            rate_first = delta
        temp += delta
        if reached is None and temp >= comfort_limit_c:
            reached = minute
    return {
        "model": "1R1C_exact_exponential",
        "safe_off_duration_min": min(max_minutes, reached) if reached is not None else max_minutes,
        "projected_temp_at_horizon_c": round(temp, 2),
        "initial_rate_c_per_min": round(rate_first, 4),
        "comfort_limit_c": comfort_limit_c,
        "note": "Estimación de demostración; requiere calibración local y no controla equipos.",
    }
