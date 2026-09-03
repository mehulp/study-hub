import json
import os
import uuid

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm

load_dotenv()

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]
JWT_ALGORITHM = "RS256"

bearer_scheme = HTTPBearer()

# Populated once at startup (Decision #29/#30 pattern, same as Items) — this
# service independently verifies tokens rather than trusting Gateway's word.
_public_key = None


def load_public_key() -> None:
    global _public_key
    response = httpx.get(f"{AUTH_SERVICE_URL}/.well-known/jwks.json")
    response.raise_for_status()
    jwk = response.json()["keys"][0]
    _public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, _public_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> uuid.UUID:
    payload = _decode(credentials.credentials)
    return uuid.UUID(payload["sub"])


def get_current_user_id_and_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> tuple[uuid.UUID, str]:
    # Used only where Board needs to call Items on the caller's behalf
    # (adding an item) — forwards the same token unchanged (Decision #30),
    # so Items applies its own ownership scoping exactly as if the caller
    # had asked directly.
    payload = _decode(credentials.credentials)
    return uuid.UUID(payload["sub"]), credentials.credentials
