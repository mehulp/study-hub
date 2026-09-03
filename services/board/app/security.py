import hashlib
import secrets
from datetime import timedelta

INVITE_TOKEN_TTL = timedelta(days=7)


def generate_invite_token() -> str:
    # High-entropy random string, not a JWT (Decision #36) — the
    # access_grants row is the source of truth, the token itself just
    # has to be unguessable.
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    # SHA-256, not Argon2id — same reasoning as refresh tokens
    # (services/auth/app/security.py): this token already has ~256 bits of
    # entropy, so the threat model is exact-match lookup, not offline
    # brute-force guessing.
    return hashlib.sha256(token.encode()).hexdigest()
