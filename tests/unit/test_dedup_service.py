"""Unit tests for dedup logic using the local FS store."""

from pathlib import Path

import pytest

from app.storage.local_fs_store import LocalFsStore
from app.utils.hashing import sha256_of_bytes


def test_exists_with_same_hash(tmp_path: Path):
    store = LocalFsStore(tmp_path)
    data = b"test content"
    h = sha256_of_bytes(data)
    store.upload("test/file.html", data, "text/html", h)
    assert store.exists_with_hash("test/file.html", h)


def test_not_exists_when_file_missing(tmp_path: Path):
    store = LocalFsStore(tmp_path)
    assert not store.exists_with_hash("missing/file.html", "anyhash")


def test_different_hash_not_duplicate(tmp_path: Path):
    store = LocalFsStore(tmp_path)
    data = b"original"
    h = sha256_of_bytes(data)
    store.upload("test/file.html", data, "text/html", h)
    assert not store.exists_with_hash("test/file.html", "differenthash")
