import json
import os
import uuid
from dataclasses import dataclass

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
    # A service token (Decision #41) has no `sub` claim — list/get are
    # user-only, so this must reject cleanly, not KeyError into a bare 500.
    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    return uuid.UUID(payload["sub"])


@dataclass
class IngestAuth:
    """Which kind of token authenticated this ingest call (Decision #41).
    A user token carries `sub` — ingest for that user, full stop. A service
    token carries `client_id` instead — no user identity at all, so the
    caller must supply owner_user_id explicitly in the request body."""

    user_id: uuid.UUID | None
    client_id: str | None

    @property
    def is_service(self) -> bool:
        return self.client_id is not None


def get_ingest_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> IngestAuth:
    payload = _decode(credentials.credentials)
    if "client_id" in payload:
        return IngestAuth(user_id=None, client_id=payload["client_id"])
    return IngestAuth(user_id=uuid.UUID(payload["sub"]), client_id=None)
