"""Shared-key authentication between the Java backend and this service.

When ``AI_API_KEY`` is set (always in production), every route except ``/health`` and ``/ready`` requires
the same value in ``X-API-Key``. Without it (local development only) the service answers anyone. The
comparison runs in constant time so the key cannot be guessed byte by byte from response times.
"""
import hmac

from fastapi import HTTPException, Request

API_KEY_HEADER = "X-API-Key"


def require_api_key(request: Request) -> None:
    expected: str | None = request.app.state.api_key
    if not expected:
        return
    supplied = request.headers.get(API_KEY_HEADER, "")
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Falta o no es válida la clave X-API-Key")
