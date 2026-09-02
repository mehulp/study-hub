import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security import (
    JWT_ALGORITHM,
    _PRIVATE_KEY,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_password_roundtrip():
    hashed = hash_password("correcthorsebatterystaple")
    assert verify_password("correcthorsebatterystaple", hashed) is True


def test_hash_password_rejects_wrong_password():
    hashed = hash_password("correcthorsebatterystaple")
    assert verify_password("wrongpassword", hashed) is False


def test_hash_password_is_salted():
    # Same input, two calls -> different hashes (Argon2 embeds a random
    # salt), even though both still verify correctly.
    hash_a = hash_password("correcthorsebatterystaple")
    hash_b = hash_password("correcthorsebatterystaple")
    assert hash_a != hash_b
    assert verify_password("correcthorsebatterystaple", hash_a) is True
    assert verify_password("correcthorsebatterystaple", hash_b) is True


def test_create_and_decode_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert "exp" in payload
    assert "iat" in payload


def test_decode_access_token_rejects_expired_token():
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(user_id),
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),
    }
    expired_token = jwt.encode(expired_payload, _PRIVATE_KEY, algorithm=JWT_ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_tampered_signature():
    token = create_access_token(uuid.uuid4())

    # Flip a character mid-signature, not at the very end: base64's trailing
    # group can carry unused padding bits that get discarded on decode, so a
    # flip at the last position can occasionally be a no-op on the actual
    # signature bytes and fail to trigger the tamper this test checks for.
    header, payload, signature = token.split(".")
    mid = len(signature) // 2
    flipped_char = "A" if signature[mid] != "A" else "B"
    tampered_signature = signature[:mid] + flipped_char + signature[mid + 1 :]
    tampered = f"{header}.{payload}.{tampered_signature}"

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(tampered)


def test_generate_refresh_token_is_unique_and_high_entropy():
    token_a = generate_refresh_token()
    token_b = generate_refresh_token()
    assert token_a != token_b
    assert len(token_a) >= 32


def test_hash_refresh_token_is_deterministic_but_one_way():
    token = generate_refresh_token()
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
