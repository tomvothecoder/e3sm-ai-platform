"""Privacy-preserving tracing and structured logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from e3sm_assist.settings import Settings

LOGGER_NAME = "e3sm_assist"
_configured = False
_instrumented_apps: set[int] = set()


class JsonFormatter(logging.Formatter):
    """Render approved log fields as a single JSON object."""

    def __init__(
        self,
        service_name: str = "e3sm-assist",
        deployment_environment: str = "development",
    ) -> None:
        """Initialize the formatter with the process service identity."""
        super().__init__()
        self.service_name = service_name
        self.deployment_environment = deployment_environment

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record without serializing arbitrary record attributes."""
        context = trace.get_current_span().get_span_context()
        payload: dict[str, object] = {
            "event": record.getMessage(),
            "level": record.levelname,
            "service.name": self.service_name,
            "deployment.environment": self.deployment_environment,
        }
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)
        if trace_id and span_id:
            payload["trace_id"] = trace_id
            payload["span_id"] = span_id
        elif context.is_valid:
            payload["trace_id"] = format(context.trace_id, "032x")
            payload["span_id"] = format(context.span_id, "016x")
        for field in (
            "request_id",
            "http_method",
            "http_route",
            "http_status_code",
            "duration_ms",
            "outcome",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_observability(settings: Settings) -> None:
    """Configure tracing, JSON logs, and FastAPI instrumentation once per process."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
    for handler in logger.handlers:
        if isinstance(handler.formatter, JsonFormatter) or handler.formatter is None:
            handler.setFormatter(
                JsonFormatter(settings.service_name, settings.deployment_environment)
            )
    if _configured:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.service_name,
            "deployment.environment": settings.deployment_environment,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.otlp_endpoint, headers=dict(settings.otlp_headers)
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _configured = True


def instrument_fastapi(app: FastAPI) -> None:
    """Instrument one FastAPI application without request payload capture."""
    app_id = id(app)
    if app_id not in _instrumented_apps:
        FastAPIInstrumentor.instrument_app(app)
        _instrumented_apps.add(app_id)


def get_logger() -> logging.Logger:
    """Return the configured application logger."""
    return logging.getLogger(LOGGER_NAME)


def log_request_complete(fields: Mapping[str, object]) -> None:
    """Emit the bounded HTTP completion event using approved fields only."""
    extra = dict(fields)
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        extra["trace_id"] = format(context.trace_id, "032x")
        extra["span_id"] = format(context.span_id, "016x")
    get_logger().info("http.request.complete", extra=extra)
