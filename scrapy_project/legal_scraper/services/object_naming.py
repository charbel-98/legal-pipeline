"""Builds the object storage key for a scraped document."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

_CONTENT_TYPE_EXT = {
    "application/msword": "doc",
    "application/pdf": "pdf",
    "application/vnd.ms-word.document.macroenabled.12": "docm",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/html": "html",
}


def build_object_key(
    source: str,
    body: str,
    partition_date: str,
    identifier: str,
    content_type: str | None = None,
    file_name: str | None = None,
    document_url: str | None = None,
) -> str:
    """Return a MinIO object key in the form:
    {source}/{body}/{partition_date}/{identifier}.{ext}
    """
    ext = _infer_extension(content_type, file_name, document_url)
    safe_body = body.lower().replace(" ", "_")
    safe_identifier = identifier.lower().replace("/", "_")
    return str(PurePosixPath(source) / safe_body / partition_date / f"{safe_identifier}.{ext}")


def _infer_extension(
    content_type: str | None,
    file_name: str | None,
    document_url: str | None,
) -> str:
    normalized = _normalize_content_type(content_type)
    if normalized in _CONTENT_TYPE_EXT:
        return _CONTENT_TYPE_EXT[normalized]

    for candidate in (file_name, _path_from_url(document_url)):
        ext = _suffix(candidate)
        if ext:
            return ext

    if normalized and "html" in normalized:
        return "html"
    return "bin"


def _normalize_content_type(ct: str | None) -> str:
    if not ct:
        return ""
    return ct.split(";", 1)[0].strip().lower()


def _path_from_url(url: str | None) -> str | None:
    if not url:
        return None
    return unquote(urlparse(url).path)


def _suffix(value: str | None) -> str | None:
    if not value:
        return None
    suffix = PurePosixPath(value).suffix.lower().lstrip(".")
    return suffix or None
