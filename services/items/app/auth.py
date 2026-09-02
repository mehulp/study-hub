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

# Populated once at startup by load_public_key() (called from main.py's
# lifespan), not fetched per-request — same pattern as Gateway (Decision
# #29). Independent from Gateway's own copy: this is Decision #30's whole
# point, each backend service verifies for itself rather than trusting
# whatever Gateway forwarded.
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
    return uuid.UUID(payload["sub"])
