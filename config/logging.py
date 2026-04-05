"""JSON structured logging configuration."""

from __future__ import annotations

import json
import logging
import sys


def get_json_logger(name: str) -> logging.Logger:
    """Return a logger that emits JSON lines to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **kwargs) -> None:
    """Emit a structured JSON log line."""
    logger.info(json.dumps({"event": event, **kwargs}))
