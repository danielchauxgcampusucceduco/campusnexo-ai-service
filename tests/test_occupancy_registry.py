import pytest

from app.infrastructure.occupancy_registry import OccupancyFilterRegistry


def update(registry, space_id, people):
    return registry.estimate(space_id, people, 415 + people * 14.5, round(people / 0.88))


def test_registry_keeps_temporal_filter_state_for_each_space():
    registry = OccupancyFilterRegistry(max_spaces=2)

    first = update(registry, "A", 20)[0]
    settled = first
    for _ in range(20):
        settled = update(registry, "A", 20)[0]
    independent = update(registry, "B", 20)[0]

    assert settled >= first
    assert independent == first


def test_registry_evicts_the_least_recently_used_space_at_capacity():
    registry = OccupancyFilterRegistry(max_spaces=2)
    for _ in range(5):
        update(registry, "A", 20)
        update(registry, "B", 20)
    update(registry, "A", 0)  # A becomes most recently used.
    update(registry, "C", 20)  # B is evicted.

    restarted_b = update(registry, "B", 0)[0]

    assert restarted_b == 0


def test_registry_requires_a_positive_capacity():
    with pytest.raises(ValueError, match="debe ser positivo"):
        OccupancyFilterRegistry(max_spaces=0)
