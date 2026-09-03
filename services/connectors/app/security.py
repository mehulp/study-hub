import hashlib
import hmac
import secrets


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
