import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from dotenv import load_dotenv
from jwt.algorithms import RSAAlgorithm

# security.py is imported directly by some tests, and is not guaranteed to
# be reached only after app.db (which also calls this). load_dotenv() is
# idempotent, so calling it again here costs nothing and removes the
# implicit dependency on import order.
load_dotenv()

password_hasher = PasswordHasher()

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
JWT_ALGORITHM = "RS256"

# Resolved relative to this file (services/auth/), not the process's current
# working directory — a relative JWT_*_KEY_PATH in .env must keep working
# regardless of where the service is launched from. An absolute path in the
# env var still works unchanged, since Path.__truediv__ discards the left
# side when the right side is already absolute.
_SERVICE_ROOT = Path(__file__).resolve().parent.parent

with open(_SERVICE_ROOT / os.environ["JWT_PRIVATE_KEY_PATH"], "rb") as f:
    _PRIVATE_KEY = f.read()

with open(_SERVICE_ROOT / os.environ["JWT_PUBLIC_KEY_PATH"], "rb") as f:
    _PUBLIC_KEY = f.read()

# A hash of a password nobody will ever type, used only so /login can run
# Argon2id verification even when no matching user exists — see
# verify_password_or_dummy below.
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))

# A static identifier for this key pair, published in the JWKS response
# (Decision #29) so a verifier could one day tell multiple keys apart during
# a rotation — irrelevant with only one key, but the field a real rotation
# story would need already exists.
KEY_ID = "auth-service-key-1"

_jwk = json.loads(RSAAlgorithm.to_jwk(load_pem_public_key(_PUBLIC_KEY)))
_jwk["alg"] = JWT_ALGORITHM
_jwk["use"] = "sig"
_jwk["kid"] = KEY_ID


def get_jwks() -> dict:
    return {"keys": [_jwk]}


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        password_hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    # Always pays the same Argon2id cost, whether or not a user was found —
    # verifying against DUMMY_PASSWORD_HASH when password_hash is None keeps
    # /login's response latency independent of account existence, closing
    # the timing side-channel a plain "skip verify if no user" would leave
    # open even though the error message itself is already generic.
    return verify_password(password, password_hash or DUMMY_PASSWORD_HASH)


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _PUBLIC_KEY, algorithms=[JWT_ALGORITHM])


def generate_refresh_token() -> str:
    # High-entropy random string, not a JWT — the DB row is the source of
    # truth (Decision #26), the token itself just has to be unguessable.
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    # SHA-256, not Argon2id: this token already has ~256 bits of entropy
    # (unlike a user-chosen password), so the threat model is exact-match
    # lookup, not offline brute-force guessing — a fast hash is the right
    # tool here, and Argon2's deliberate slowness would just cost latency
    # on every /refresh call for no security benefit.
    return hashlib.sha256(token.encode()).hexdigest()
