import logging
from pathlib import Path

from e3sm_ai_platform.infrastructure.observability import (
    LOGGER_NAME,
    JsonFormatter,
    configure_observability,
    format_startup_configuration,
    startup_configuration,
)
from e3sm_ai_platform.infrastructure.settings import Settings


def test_local_collector_filters_prohibited_trace_attributes_before_batching() -> None:
    """Configure privacy filtering before local Jaeger trace export."""
    collector_config = (
        Path(__file__).parents[2] / "deploy/observability/otel-collector.yaml"
    ).read_text()

    assert "attributes/privacy:\n    actions:" in collector_config
    assert "- key: net.peer.ip\n        action: delete" in collector_config
    assert "- key: http.user_agent\n        action: delete" in collector_config
    assert "processors: [attributes/privacy, batch]" in collector_config


def test_configure_observability_uses_configured_log_identity() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    original_formatters = {handler: handler.formatter for handler in logger.handlers}
    settings = Settings(service_name="observability-test", deployment_environment="test")

    try:
        configure_observability(settings)
        formatter = next(
            handler.formatter
            for handler in logger.handlers
            if isinstance(handler.formatter, JsonFormatter)
        )

        assert formatter.service_name == "observability-test"
        assert formatter.deployment_environment == "test"
    finally:
        for handler in list(logger.handlers):
            if handler not in original_formatters:
                logger.removeHandler(handler)
        for handler, formatter in original_formatters.items():
            handler.setFormatter(formatter)


def test_startup_configuration_excludes_secrets() -> None:
    settings = Settings(
        assistant_generator="livai",
        livai_api_key="secret-key",
        livai_model="example-model",
        livai_base_url="https://livai.example.test/",
        otlp_endpoint="https://otel.example.test/v1/traces",
        otlp_headers=(("Authorization", "Bearer secret-token"),),
        retrieval_mode="hybrid",
    )

    configuration = startup_configuration(settings)
    summary = format_startup_configuration(settings)
    record = logging.LogRecord(
        LOGGER_NAME,
        logging.INFO,
        __file__,
        0,
        summary,
        (),
        None,
    )
    record.human_readable = True
    rendered = JsonFormatter().format(record)

    assert configuration["inference_backend"] == "livai"
    assert configuration["livai_enabled"] is True
    assert configuration["otlp_headers_configured"] is True
    assert "secret-key" not in rendered
    assert "secret-token" not in rendered
    assert rendered == summary
    assert "E3SM AI Platform startup configuration" in rendered
    assert "Backend: livai" in rendered
    assert "OTLP headers: configured" in rendered
