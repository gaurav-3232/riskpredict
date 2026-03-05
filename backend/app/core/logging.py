import structlog
import logging
import sys
import os


def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_prod = os.getenv("ENVIRONMENT", "development") == "production"

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if is_prod:
        # JSON output for production (log aggregators)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty output for development
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )


def get_logger(name: str = __name__):
    return structlog.get_logger(name)
