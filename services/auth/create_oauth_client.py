"""One-off setup script to register a new OAuth2 client (Decision #41).

Not an API endpoint — matches Decision #8's reasoning: there's no real
audience for a self-service "register a client" flow at this project's
scale, just a developer running this once per client that needs to exist.

Usage: ./venv/bin/python create_oauth_client.py <client_id> <client_name>
Prints the plaintext client_secret exactly once — only its hash is stored.
"""
import sys

from app.db import SessionLocal
from app.models import OAuthClient
from app.security import generate_client_secret, hash_client_secret


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: create_oauth_client.py <client_id> <client_name>")
        sys.exit(1)

    client_id, client_name = sys.argv[1], sys.argv[2]
    secret = generate_client_secret()

    db = SessionLocal()
    try:
        db.add(
            OAuthClient(
                client_id=client_id,
                client_secret_hash=hash_client_secret(secret),
                client_name=client_name,
            )
        )
        db.commit()
    finally:
        db.close()

    print(f"client_id:     {client_id}")
    print(f"client_secret: {secret}")
    print("The secret above will not be shown again — store it now.")


if __name__ == "__main__":
    main()
