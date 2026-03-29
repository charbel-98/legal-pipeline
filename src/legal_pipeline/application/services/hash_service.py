import hashlib


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
