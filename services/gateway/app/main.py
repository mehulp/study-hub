import json
import os
import re
from contextlib import asynccontextmanager

import httpx
import jwt as pyjwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from jwt.algorithms import RSAAlgorithm

load_dotenv()

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]
ITEMS_SERVICE_URL = os.environ["ITEMS_SERVICE_URL"]
BOARD_SERVICE_URL = os.environ["BOARD_SERVICE_URL"]
CONNECTORS_SERVICE_URL = os.environ["CONNECTORS_SERVICE_URL"]
CORS_ALLOWED_ORIGINS = os.environ["CORS_ALLOWED_ORIGINS"].split(",")
JWT_ALGORITHM = "RS256"

# Routing table (Decision #31): one entry per backend service. Gateway's
# code never changes to add a new backend — this table just grows. Items
# and Board are both proof of that promise: no logic below changed either
# time. Connectors is the first exception — see
# OPAQUE_CREDENTIAL_PATH_PATTERNS just below, a real gap the routing table
# alone couldn't paper over.
ROUTES = [
    {"prefix": "/auth", "target": AUTH_SERVICE_URL},
    {"prefix": "/items", "target": ITEMS_SERVICE_URL},
    {"prefix": "/board", "target": BOARD_SERVICE_URL},
    {"prefix": "/connectors", "target": CONNECTORS_SERVICE_URL},
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

# Not public — these still require a real credential — but the credential
# is an opaque, resource-scoped push token (Decision #42), never an
# Auth-issued JWT. Gateway's own coarse check can only verify JWTs (it only
# holds Auth's public key), so for these paths it can't do anything useful
# and must not try: attempting to JWT-decode a push token always fails,
# rejecting a legitimately authenticated request before it ever reaches
# Connectors, which does the real check. Exact-string PUBLIC_PATHS can't
# express this (the connection id is dynamic), hence a pattern instead.
OPAQUE_CREDENTIAL_PATH_PATTERNS = [
    re.compile(r"^/connectors/connections/[^/]+/sync$"),
]

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

# The extension never needed this (host_permissions exempts it from CORS
# entirely, Decision #46) — the web UI is a plain webpage on its own origin
# (localhost:5173) and gets no such exemption, so Gateway must opt it in
# explicitly. allow_credentials is off: the web UI sends its access token
# as an Authorization header, not via cookies, so requests aren't
# "credentialed" in the fetch/CORS sense.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _match_route(path: str) -> dict:
    # Boundary check matters: plain startswith() would let "/itemsxyz" match
    # the "/items" prefix (same prefix, wrong path), producing a malformed
    # target URL. The prefix must be the whole path or be followed by "/".
    for route in ROUTES:
        prefix = route["prefix"]
        if path == prefix or path.startswith(prefix + "/"):
            return route
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


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

    if path not in PUBLIC_PATHS and not any(
        pattern.match(path) for pattern in OPAQUE_CREDENTIAL_PATH_PATTERNS
    ):
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

    try:
        async with httpx.AsyncClient() as client:
            upstream_response = await client.request(
                request.method,
                target_url,
                params=request.query_params,
                content=body,
                headers=forward_headers,
                # 30s, not the original 10s — a legitimately slow upstream
                # call (e.g. a large batch sync) should get a real chance
                # to finish rather than being cut off aggressively.
                timeout=30.0,
            )
    except httpx.TimeoutException:
        # Previously unhandled — any upstream timeout crashed through as
        # Starlette's default plain-text 500 page, which a JSON-only client
        # (like the browser extension) can't even parse into a readable
        # error. Real bug, caught by an actual large sync through a real
        # browser, not by any test — worth remembering that "no test caught
        # it" doesn't mean "it can't happen."
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream service took too long to respond",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream service error: {exc}",
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
