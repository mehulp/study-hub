import json
import os
from contextlib import asynccontextmanager

import httpx
import jwt as pyjwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from jwt.algorithms import RSAAlgorithm

load_dotenv()

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]
ITEMS_SERVICE_URL = os.environ["ITEMS_SERVICE_URL"]
BOARD_SERVICE_URL = os.environ["BOARD_SERVICE_URL"]
JWT_ALGORITHM = "RS256"

# Routing table (Decision #31): one entry per backend service. Gateway's
# code never changes to add a new backend — this table just grows. Items
# and Board are both proof of that promise: no logic below changed either time.
ROUTES = [
    {"prefix": "/auth", "target": AUTH_SERVICE_URL},
    {"prefix": "/items", "target": ITEMS_SERVICE_URL},
    {"prefix": "/board", "target": BOARD_SERVICE_URL},
]

# Secure by default: everything under a routed prefix requires a valid
# access token UNLESS it's explicitly listed here. A newly added protected
# endpoint that's simply not added to this set stays protected — the
# opposite (an allowlist of protected paths) would silently leak a
# forgotten endpoint as public instead.
PUBLIC_PATHS = {
    "/auth/signup",
    "/auth/login",
    "/auth/refresh",
    "/auth/logout",
}

# Hop-by-hop headers that must not be blindly forwarded either direction —
# httpx recalculates framing (content-length, chunked transfer, gzip) on
# both legs, so relaying the upstream's original values would desync them.
_HOP_BY_HOP_HEADERS = {"content-length", "transfer-encoding", "content-encoding", "connection"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fetched once at startup (Decision #29) rather than per-request — a
    # real rotation story would re-fetch periodically or on a kid mismatch,
    # out of scope for this pass.
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{AUTH_SERVICE_URL}/.well-known/jwks.json")
        response.raise_for_status()

    jwk = response.json()["keys"][0]
    app.state.public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))
    yield


app = FastAPI(title="Gateway", lifespan=lifespan)


def _match_route(path: str) -> dict:
    route = next((r for r in ROUTES if path.startswith(r["prefix"])), None)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return route


def _require_valid_token(request: Request) -> None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ")
    try:
        # Coarse-grained check only: is this a validly signed, unexpired
        # token. Fine-grained authorization (can *this* user do *this*
        # thing) is each backend service's own job (Decision #30) — the
        # original token is forwarded unchanged below so it can re-verify.
        pyjwt.decode(token, request.app.state.public_key, algorithms=[JWT_ALGORITHM])
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )


@app.api_route(
    "/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def proxy(full_path: str, request: Request) -> Response:
    path = "/" + full_path
    route = _match_route(path)

    if path not in PUBLIC_PATHS:
        _require_valid_token(request)

    # `or "/"` matters: a request to exactly the routed prefix (e.g. just
    # "/items", no trailing path) strips down to an empty remainder, which
    # would forward as a bare host URL with no path at all — most backend
    # routes (including Items' own "/") expect at least "/".
    target_url = route["target"] + (path[len(route["prefix"]):] or "/")
    body = await request.body()
    forward_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS
    }

    async with httpx.AsyncClient() as client:
        upstream_response = await client.request(
            request.method,
            target_url,
            params=request.query_params,
            content=body,
            headers=forward_headers,
            timeout=10.0,
        )

    response_headers = {
        k: v
        for k, v in upstream_response.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
