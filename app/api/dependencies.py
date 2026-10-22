from fastapi import Request

from app.infrastructure.occupancy_registry import OccupancyFilterRegistry
from app.infrastructure.vision import YoloCounter


def get_occupancy_registry(request: Request) -> OccupancyFilterRegistry:
    return request.app.state.occupancy_registry


def get_vision_counter(request: Request) -> YoloCounter:
    return request.app.state.vision_counter
