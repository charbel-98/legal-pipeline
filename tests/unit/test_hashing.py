from app.utils.hashing import sha256_of_bytes


def test_sha256_deterministic():
    data = b"hello world"
    assert sha256_of_bytes(data) == sha256_of_bytes(data)


def test_sha256_known_value():
    # echo -n "hello world" | sha256sum
    assert sha256_of_bytes(b"hello world") == (
        "b94d27b9934d3e08a52e52d7da7dabfac484efe04294e576b5"
        "7c3bbb56b571b7"
    )


def test_sha256_different_inputs_produce_different_hashes():
    assert sha256_of_bytes(b"foo") != sha256_of_bytes(b"bar")
