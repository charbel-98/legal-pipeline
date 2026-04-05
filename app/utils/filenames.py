"""Extension mapping from MIME content types."""

_EXT_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-word.document.macroenabled.12": "docm",
    "text/html": "html",
}


def ext_for_content_type(content_type: str | None) -> str:
    return _EXT_MAP.get(content_type or "", "bin")
