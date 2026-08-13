import logging

from e3sm_assist.observability import LOGGER_NAME, JsonFormatter, configure_observability
from e3sm_assist.settings import Settings


def test_configure_observability_uses_configured_log_identity() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    original_formatters = [handler.formatter for handler in logger.handlers]
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
        for handler, formatter in zip(logger.handlers, original_formatters, strict=True):
            handler.setFormatter(formatter)
