"""Local filesystem object store — used in tests and local dev without MinIO."""

from __future__ import annotations

from pathlib import Path

from app.storage.object_store import ObjectStore
from app.utils.hashing import sha256_of_bytes


class LocalFsStore(ObjectStore):
    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = self._base / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def upload(self, key: str, data: bytes, content_type: str, file_hash: str) -> None:
        self._path(key).write_bytes(data)

    def download(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists_with_hash(self, key: str, file_hash: str) -> bool:
        p = self._path(key)
        if not p.exists():
            return False
        return sha256_of_bytes(p.read_bytes()) == file_hash
