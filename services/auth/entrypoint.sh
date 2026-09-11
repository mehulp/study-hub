#!/bin/sh
set -e

# A git-clone-based deploy (Railway) never has these files -- they're
# .gitignore'd real private key material, present in the local dev image
# only because they were generated once and picked up by `COPY . .`
# (Decision #87). Only write them from env vars when they're genuinely
# missing, so local dev's already-present files are never touched or
# overwritten -- this is what keeps `docker compose up` byte-for-byte
# unchanged after this file was added.
#
# Values are base64 (JWT_PRIVATE_KEY_PEM_B64 / JWT_PUBLIC_KEY_PEM_B64), not
# raw PEM text -- a raw multi-line PEM pasted into a single-line dashboard
# input reliably loses its newlines, which breaks PEM parsing with a
# "MalformedFraming" error (found live on Railway). Base64 has no newlines
# to lose, so it survives a single-line field intact.
if [ ! -f private_key.pem ] && [ -n "$JWT_PRIVATE_KEY_PEM_B64" ]; then
  echo "$JWT_PRIVATE_KEY_PEM_B64" | base64 -d > private_key.pem
fi
if [ ! -f public_key.pem ] && [ -n "$JWT_PUBLIC_KEY_PEM_B64" ]; then
  echo "$JWT_PUBLIC_KEY_PEM_B64" | base64 -d > public_key.pem
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
