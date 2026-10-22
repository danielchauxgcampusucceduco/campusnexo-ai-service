"""Bounded, thread-safe state for the per-space occupancy filters."""
from collections import OrderedDict
from threading import Lock

from app.domain.occupancy import KalmanOccupancy


class OccupancyFilterRegistry:
    def __init__(self, max_spaces: int = 2_000):
        if max_spaces < 1:
            raise ValueError("max_spaces debe ser positivo")
        self._max_spaces = max_spaces
        self._filters: OrderedDict[str, KalmanOccupancy] = OrderedDict()
        self._lock = Lock()

    def estimate(
        self,
        space_id: str,
        yolo_people: int | None,
        co2_ppm: float,
        wifi_devices: int,
        outdoor_co2_ppm: float = 415.0,
    ) -> tuple[int, float]:
        with self._lock:
            estimator = self._filters.setdefault(space_id, KalmanOccupancy())
            self._filters.move_to_end(space_id)
            while len(self._filters) > self._max_spaces:
                self._filters.popitem(last=False)
            return estimator.update(yolo_people, co2_ppm, wifi_devices, outdoor_co2_ppm)
