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

# Populated once at startup (same pattern as Items/Board, Decision #29/#30)
# — Connectors independently verifies user tokens rather than trusting
# Gateway's word.
_public_key = None


def load_public_key() -> None:
    global _public_key
    response = httpx.get(f"{AUTH_SERVICE_URL}/.well-known/jwks.json")
    response.raise_for_status()
    jwk = response.json()["keys"][0]
    _public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> uuid.UUID:
    try:
        payload = jwt.decode(credentials.credentials, _public_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    # A service token (Decision #41) has no `sub` claim — /connections is
    # user-only, so this must reject cleanly, not KeyError into a bare 500.
    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    return uuid.UUID(payload["sub"])
