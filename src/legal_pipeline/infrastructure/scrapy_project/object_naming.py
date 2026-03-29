from pathlib import PurePosixPath


def build_object_name(
    source: str,
    body: str,
    partition_date: str,
    identifier: str,
    content_type: str,
) -> str:
    extension = "html" if "html" in content_type else "bin"
    safe_body = body.lower().replace(" ", "_")
    safe_identifier = identifier.lower().replace("/", "_")
    return str(PurePosixPath(source) / safe_body / partition_date / f"{safe_identifier}.{extension}")
