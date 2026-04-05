"""Structured JSON logger."""

from __future__ import annotations

import json
import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


def log(logger: logging.Logger, event: str, **kwargs) -> None:
    logger.info(json.dumps({"event": event, **kwargs}))
