"""Centralized logging configuration for the Invoice Manager backend."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure stdlib logging with a consistent format.

    Call once at application startup (in the FastAPI lifespan handler).
    """
    fmt = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        stream=sys.stderr,
    )
    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("weasyprint").setLevel(logging.WARNING)
