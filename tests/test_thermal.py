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

    assert result["model"] == "1R1C_forward_euler"
    assert result["safe_off_duration_min"] <= 12
    assert result["projected_temp_at_horizon_c"] < 20
    assert "no controla equipos" in result["note"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("resistance_c_per_kw", 0), ("capacitance_kwh_per_c", -1)],
)
def test_model_rejects_non_positive_physical_parameters(field, value):
    with pytest.raises(ValueError, match="R y C deben ser positivos"):
        simulate_free_warming(20, 14, 10, 1, **{field: value})


def test_model_rejects_negative_load_or_duration():
    with pytest.raises(ValueError, match="no pueden ser negativas"):
        simulate_free_warming(20, 14, -1, 1)

    with pytest.raises(ValueError, match="no pueden ser negativas"):
        simulate_free_warming(20, 14, 1, 1, max_minutes=-1)


def test_comfort_already_reached_produces_zero_safe_off_time():
    result = simulate_free_warming(25, 20, 0, 0, comfort_limit_c=24.5)

    assert result["safe_off_duration_min"] == 0
