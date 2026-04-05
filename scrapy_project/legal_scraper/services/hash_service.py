"""Hashing helpers for the Scrapy layer (delegates to app.utils)."""

from app.utils.hashing import sha256_of_bytes

__all__ = ["sha256_of_bytes"]
