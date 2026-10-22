"""Request correlation and structured access metadata for HTTP observability."""
import logging
import re
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger("campusnexo.http")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    supplied_id = request.headers.get("x-request-id", "")
    request_id = supplied_id if REQUEST_ID_PATTERN.fullmatch(supplied_id) else uuid.uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http_request_completed",
        extra={
            "request_id": request_id,
            "http_method": request.method,
            "http_path": request.url.path,
            "http_status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1_000, 2),
        },
    )
    return response
