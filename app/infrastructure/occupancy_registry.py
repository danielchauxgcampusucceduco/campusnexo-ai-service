"""Bounded, thread-safe state for the per-space occupancy filters."""
from collections import OrderedDict
from threading import Lock

from app.domain.occupancy import KalmanOccupancy
from app.settings import MAX_TRACKED_SPACES


class OccupancyFilterRegistry:
    def __init__(self, max_spaces: int = MAX_TRACKED_SPACES):
        if isinstance(max_spaces, bool) or not isinstance(max_spaces, int) or max_spaces < 1:
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
        if not isinstance(space_id, str) or not space_id.strip():
            raise ValueError("space_id no puede estar vacío")
        space_id = space_id.strip()
        with self._lock:
            estimator = self._filters.get(space_id)
            is_new = estimator is None
            if estimator is None:
                estimator = KalmanOccupancy()
            result = estimator.update(yolo_people, co2_ppm, wifi_devices, outdoor_co2_ppm)
            if is_new:
                self._filters[space_id] = estimator
            self._filters.move_to_end(space_id)
            while len(self._filters) > self._max_spaces:
                self._filters.popitem(last=False)
            return result
