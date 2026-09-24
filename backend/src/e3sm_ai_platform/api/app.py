"""FastAPI application for E3SM Compass."""

from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from e3sm_ai_platform.application.service import CompassService
from e3sm_ai_platform.domain.models import QueryRequest, QueryResponse
from e3sm_ai_platform.infrastructure.observability import (
    configure_observability,
    instrument_fastapi,
    log_request_complete,
)
from e3sm_ai_platform.infrastructure.settings import load_settings


@lru_cache(maxsize=1)
def get_service() -> CompassService:
    """Return the process-cached application service."""
    return CompassService()


def allowed_cors_origins() -> list[str]:
    """Read safe comma-separated CORS origins for local prototype frontend access."""
    return list(load_settings().cors_allow_origins)


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach server-generated request IDs and log bounded request outcomes."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process an HTTP request without recording headers or bodies."""
        started = perf_counter()
        request_id = uuid4().hex
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            log_request_complete(
                {
                    "request_id": request_id,
                    "http_method": request.method,
                    "http_route": route_path,
                    "http_status_code": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "outcome": "success" if status_code < 500 else "error",
                }
            )


app = FastAPI(title="E3SM Compass", version="0.1.0")
_settings = load_settings()
configure_observability(_settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "traceparent", "tracestate"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestObservabilityMiddleware)
instrument_fastapi(app)


@app.get("/health")
def health(service: Annotated[CompassService, Depends(get_service)]) -> dict[str, object]:
    """Return the health endpoint response."""
    return service.health()


@app.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    service: Annotated[CompassService, Depends(get_service)],
) -> QueryResponse:
    """Return the response for a query endpoint request."""
    return service.query(request)
