from fastapi import Request

from app.infrastructure.vision import YoloCounter


def get_vision_counter(request: Request) -> YoloCounter:
    return request.app.state.vision_counter
