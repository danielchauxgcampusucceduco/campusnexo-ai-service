import pytest

from app.domain.thermal import simulate_free_warming


def test_model_reports_a_stable_schema_and_respects_the_horizon():
    result = simulate_free_warming(
        current_temp_c=20,
        outside_temp_c=14,
        occupancy=10,
        lighting_kw=1.2,
        max_minutes=12,
    )

    assert result["model"] == "1R1C_exact_exponential"
    assert result["safe_off_duration_min"] <= 12
    assert result["projected_temp_at_horizon_c"] < 20
    assert "no controla equipos" in result["note"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("resistance_c_per_kw", 0), ("capacitance_kwh_per_c", -1)],
)
def test_model_rejects_non_positive_physical_parameters(field, value):
    with pytest.raises(ValueError, match=field):
        simulate_free_warming(20, 14, 10, 1, **{field: value})


def test_model_rejects_negative_load_or_duration():
    with pytest.raises(ValueError, match="occupancy"):
        simulate_free_warming(20, 14, -1, 1)

    with pytest.raises(ValueError, match="max_minutes"):
        simulate_free_warming(20, 14, 1, 1, max_minutes=-1)


def test_comfort_already_reached_produces_zero_safe_off_time():
    result = simulate_free_warming(25, 20, 0, 0, comfort_limit_c=24.5)

    assert result["safe_off_duration_min"] == 0


def test_exact_solution_is_monotonic_and_does_not_overshoot_equilibrium():
    result = simulate_free_warming(
        20, 14, 10, 1.2,
        resistance_c_per_kw=10,
        capacitance_kwh_per_c=0.001,
        comfort_limit_c=35,
        max_minutes=20,
    )
    equilibrium = 14 + 10 * (10 * 0.115 + 1.2)

    assert 20 <= result["projected_temp_at_horizon_c"] <= equilibrium


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_temp_c", float("nan")),
        ("outside_temp_c", float("inf")),
        ("lighting_kw", -1),
        ("occupancy", 1001),
        ("resistance_c_per_kw", 0),
        ("capacitance_kwh_per_c", 1001),
        ("comfort_limit_c", 40),
        ("max_minutes", 121),
    ],
)
def test_thermal_domain_rejects_non_finite_and_out_of_range_inputs(field, value):
    values = {
        "current_temp_c": 20,
        "outside_temp_c": 14,
        "occupancy": 10,
        "lighting_kw": 1,
    }

    with pytest.raises(ValueError, match=field):
        simulate_free_warming(**(values | {field: value}))


@pytest.mark.parametrize(("field", "value"), [("occupancy", True), ("occupancy", 1.5), ("max_minutes", 2.5)])
def test_thermal_domain_requires_integer_count_and_horizon(field, value):
    with pytest.raises(ValueError, match=f"{field}.*entero"):
        simulate_free_warming(**({"current_temp_c": 20, "outside_temp_c": 14, "occupancy": 1,
                                  "lighting_kw": 1} | {field: value}))
