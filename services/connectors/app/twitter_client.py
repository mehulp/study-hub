import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

TWITTER_CLIENT_ID = os.environ["TWITTER_CLIENT_ID"]
TWITTER_CLIENT_SECRET = os.environ["TWITTER_CLIENT_SECRET"]
TWITTER_REDIRECT_URI = os.environ["TWITTER_REDIRECT_URI"]

AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
SCOPES = "bookmark.read users.read offline.access"


class TwitterOAuthError(Exception):
    """X's authorize or token endpoint rejected the request, or was
    unreachable — a real failure, distinct from a user simply not having
    completed the flow yet."""


def build_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": TWITTER_CLIENT_ID,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str, code_verifier: str) -> dict:
    """POSTs to X's token endpoint using HTTP Basic Auth (we're a
    confidential client — Connectors runs server-side and can safely hold
    TWITTER_CLIENT_SECRET, unlike a browser-based app). Returns X's raw
    token response: {access_token, refresh_token, expires_in, ...}."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": TWITTER_REDIRECT_URI,
                    "code_verifier": code_verifier,
                },
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise TwitterOAuthError(f"Token exchange request failed: {exc}") from exc

    if response.status_code != 200:
        raise TwitterOAuthError(f"Token exchange returned {response.status_code}: {response.text}")

    return response.json()
