import base64
import hashlib
import hmac
import secrets


def generate_oauth_state() -> str:
    # A CSRF token: proves the browser arriving at /callback is the same
    # one we redirected to X, not an attacker who guessed/intercepted a
    # callback URL and is replaying it against a different victim's
    # session.
    return secrets.token_urlsafe(32)


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge). X requires PKCE's S256
    method (RFC 7636) on every app, confidential or not — not just the
    "public client can't hold a secret" case PKCE is usually taught for."""
    code_verifier = secrets.token_urlsafe(64)  # 43-128 chars required; this is 86
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


def generate_push_token() -> str:
    # High-entropy random string, not a JWT (Decision #42) — the
    # connections row is the source of truth, the token itself just has to
    # be unguessable.
    return secrets.token_urlsafe(32)


def hash_push_token(token: str) -> str:
    # SHA-256, not Argon2id — same reasoning as refresh/invite tokens: this
    # token is system-generated with high entropy, not a human-chosen
    # password, so the threat model is exact-match lookup, not offline
    # brute-force guessing.
    return hashlib.sha256(token.encode()).hexdigest()


def verify_push_token(token: str, token_hash: str) -> bool:
    # Constant-time comparison — same reasoning as Auth's verify_client_secret.
    return hmac.compare_digest(hash_push_token(token), token_hash)
