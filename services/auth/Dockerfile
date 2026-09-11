FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8001

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/.well-known/jwks.json')"

# Migrations run on every container start, not as a separate manual step —
# Decision #34's schema auto-bootstrap is what makes this safe against a
# fresh database with no prior setup. entrypoint.sh (Decision #87) adds one
# thing before that: writing the JWT key files from env vars, but only if
# they're not already present (see the script's own comment).
CMD ["./entrypoint.sh"]
