from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

CONTENT_TYPE_EXTENSION_MAP = {
    "application/msword": "doc",
    "application/pdf": "pdf",
    "application/vnd.ms-word.document.macroenabled.12": "docm",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/html": "html",
}


def build_object_name(
    source: str,
    body: str,
    partition_date: str,
    identifier: str,
    content_type: str | None = None,
    file_name: str | None = None,
    document_url: str | None = None,
) -> str:
    extension = infer_extension(
        content_type=content_type,
        file_name=file_name,
        document_url=document_url,
    )
    safe_body = body.lower().replace(" ", "_")
    safe_identifier = identifier.lower().replace("/", "_")
    return str(
        PurePosixPath(source) / safe_body / partition_date / f"{safe_identifier}.{extension}"
    )


def infer_extension(
    content_type: str | None = None,
    file_name: str | None = None,
    document_url: str | None = None,
) -> str:
    normalized_content_type = _normalize_content_type(content_type)
    if normalized_content_type in CONTENT_TYPE_EXTENSION_MAP:
        return CONTENT_TYPE_EXTENSION_MAP[normalized_content_type]

    for candidate in (file_name, _path_from_url(document_url)):
        extension = _suffix(candidate)
        if extension:
            return extension

    if normalized_content_type and "html" in normalized_content_type:
        return "html"
    return "bin"


def _normalize_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _path_from_url(url: str | None) -> str | None:
    if not url:
        return None
    return unquote(urlparse(url).path)


def _suffix(value: str | None) -> str | None:
    if not value:
        return None
    suffix = PurePosixPath(value).suffix.lower().lstrip(".")
    return suffix or None
