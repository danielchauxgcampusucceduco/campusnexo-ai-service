import pytest
from pydantic import ValidationError

from app.api.schemas import OccupancyBatchInput
from app.settings import MAX_OCCUPANCY_BATCH_ITEMS


def reading(space_id: str) -> dict:
    return {"space_id": space_id, "co2_ppm": 600, "wifi_devices": 10}


def test_batch_contract_requires_unique_spaces_and_non_empty_input():
    with pytest.raises(ValidationError, match="space_id debe ser único"):
        OccupancyBatchInput(measurements=[reading("A-301"), reading("A-301")])

    with pytest.raises(ValidationError):
        OccupancyBatchInput(measurements=[])


def test_batch_contract_publishes_a_bounded_measurement_count():
    payload = OccupancyBatchInput(measurements=[reading(f"A-{index}") for index in range(MAX_OCCUPANCY_BATCH_ITEMS)])
    assert len(payload.measurements) == MAX_OCCUPANCY_BATCH_ITEMS

    with pytest.raises(ValidationError):
        OccupancyBatchInput(measurements=[reading(f"A-{index}") for index in range(MAX_OCCUPANCY_BATCH_ITEMS + 1)])
