"""
logging_config.py - Centralized logging configuration.

Provides consistent logging setup across all modules.
"""

from __future__ import annotations

import functools
import logging
import sys
from typing import Callable, TypeVar

T = TypeVar("T")


def setup_logging(level: int = logging.INFO, json_format: bool = False) -> None:
    """Configure root logger with consistent formatting.

    Args:
        level: Logging level.
        json_format: If True, emit JSON-like log lines.
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    if json_format:
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
            '"module":"%(name)s","message":"%(message)s"}',
            datefmt="%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(name)-20s] %(levelname)-7s %(message)s",
            datefmt="%H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)


def graceful(default_factory: Callable[[], T], log_level: int = logging.ERROR):
    """Decorator that catches exceptions and returns a default value.

    NOTE: Available for future use. In current code, functions still
    handle errors explicitly with local try/except blocks.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:  # pragma: no cover - defensive wrapper
                logger = logging.getLogger(func.__module__)
                logger.log(
                    log_level,
                    "%s failed: %s: %s",
                    func.__name__,
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                return default_factory()

        return wrapper

    return decorator
