# Daily Startup — Quick Reference

This covers **local development only**. For the production setup (Railway + Cloudflare), see `docs/deployment.md`.

The whole stack is containerized (Decision #35), so daily startup is one command, not a per-service manual routine.

**Only one of mp-project-study-hub / bookmarks-hub runs at a time.** `bookmarks-hub`
(`/home/mehul/projects/bookmarks-hub`) is the separate personal project this one was cloned
from, deliberately sharing the same ports rather than each getting its own — simpler, and
easier to shut down, at the cost of never running both simultaneously. `start-dev.sh` in
both projects checks for this and refuses to start if the other one's containers are
already up, rather than failing with a confusing Docker port-bind error.

Run everything **inside the WSL2 Ubuntu terminal**, not PowerShell. The project lives at
`/home/mehul/projects/mp-project-study-hub` (inside WSL). Driving it from Windows would route every
file operation through the `\\wsl$` 9p filesystem — slow builds, and relative `build:` paths in
`docker-compose.yml` misbehave. VS Code's integrated terminal is already an Ubuntu shell when
connected via the WSL extension, so that's the easiest place.

## The stack

| Service | Port | Migrations | Notes |
|---|---|---|---|
| `postgres` | 5432 | — | schema-per-service; `postgres_data` volume |
| `gateway` | 8000 | no | entry point |
| `auth` | 8001 | alembic | issues JWTs; JWKS healthcheck |
| `items` | 8002 | alembic | depends on auth |
| `board` | 8003 | alembic | |
| `connectors` | 8004 | alembic | |

Each service runs `alembic upgrade head` on container start, so migrations apply themselves.

## First-time setup (fresh clone only)

`docker compose up` reads `POSTGRES_PASSWORD` and `OAUTH_CLIENT_SECRET` from a root `.env`
file (gitignored, Decision #66) — without it, Postgres itself won't start correctly.

```bash
cp .env.example .env
# Generate a real OAUTH_CLIENT_SECRET (prints once, paste it into .env):
cd services/auth && ./venv/bin/python create_oauth_client.py connectors-service "Connectors Service"
```

`POSTGRES_PASSWORD` can be any value — it only needs to match between `.env` and whatever
already-running Postgres volume you're pointing at. `TWITTER_CLIENT_*` vars can stay blank
unless you're actually testing the Twitter OAuth flow.

### Per-service venvs and .env (only needed to run a service's tests outside Docker)

Each service needs its own venv and `.env` — Docker itself doesn't need any of this, only
`./venv/bin/python -m pytest` does:

```bash
for svc in auth items board connectors gateway; do
  (cd services/$svc && python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt && cp .env.example .env)
done
```

Two services' `.env` need one more thing beyond what `.env.example` copies, because their
app code reads an env var unconditionally at import time even when the feature it's for
isn't being exercised:

- **connectors/.env**: add blank `TWITTER_CLIENT_ID=` / `TWITTER_CLIENT_SECRET=` /
  `TWITTER_REDIRECT_URI=` lines — `app/twitter_client.py` reads these at module load
  regardless of whether any test touches the Twitter connector.
- **gateway/.env**: add `CORS_ALLOWED_ORIGINS=http://localhost:5173` — `app/main.py` reads
  it the same way.

Then run one service's suite with `cd services/<name> && ./venv/bin/python -m pytest -q`,
or all five with `bash run-tests.sh` (Postgres must be up first).

**Known flakiness:** an isolated test occasionally fails with "Invalid or expired access
token" — a pre-existing timing issue in how the session-scoped Auth/Items test subprocess
fixtures start up, not a real bug. It's never reproduced on an immediate re-run of the same
test or the full suite; if you hit it, just re-run.

## Morning: starting up for the day

```bash
# 0. Start Docker Desktop on Windows first — WSL2 integration needs it running.
#    Wait until the whale icon stops animating.

# 1. In the Ubuntu terminal (or VS Code's integrated terminal):
cd /home/mehul/projects/mp-project-study-hub
bash start-dev.sh
```

Starts the backend stack (all six Docker services, health-gated dependency order) **and** the
web UI's Vite dev server together, in one command. Idempotent — safe to re-run any time; it
skips anything already running rather than starting a duplicate.

This exists because the two were easy to get out of sync: the web UI is deliberately separate
from Compose (Decision #49, since it's not part of the same container stack), which means
restarting/rebuilding the backend never brings Vite back with it. That gap caused a real
"unable to reach that url" confusion mid-session once already — Docker and the tunnel were all
healthy, but the actual web UI dev server had quietly died and nothing restarted it. One script
starting both removes the need to remember two separate steps.

If you changed any service's code since last time, rebuild the backend first:

```bash
docker compose up -d --build
```

(`start-dev.sh` itself doesn't rebuild — plain `up -d` reuses existing images. Run the `--build`
form above, then `bash start-dev.sh` again to bring the web UI up alongside it.)

Then confirm everything's actually healthy:

```bash
docker compose ps
```

All six should show `running` and, where a healthcheck is defined, `(healthy)`. If `auth` is
stuck at `starting`, give it ~10s — its healthcheck has a `start_period`.

`node_modules` is already installed for the web UI; only re-run `npm install` after a
`package.json` change.

### ngrok tunnel (only needed for Twitter OAuth testing — not part of daily startup)

```bash
ngrok http 8000
```

Gives Gateway a real public HTTPS URL for X's OAuth callback (Decision #56). Not something to
run every day — only when actually testing the Twitter connect flow. Check it's alive with
`curl http://127.0.0.1:4040/api/tunnels`.

### Sanity check after a long gap or a fresh machine

```bash
bash check-dev-env.sh
```

## Python venvs

Each service has its **own** venv at `services/<service>/venv` (Python 3.12.3). You only need
these for running tests, linting, or IDE autocomplete — **not** for running the app, which
happens inside containers.

```bash
# Activate one (auth, items, board, connectors, gateway):
cd services/auth
source venv/bin/activate
# ... work ...
deactivate
```

Or skip activation entirely and call the interpreter directly:

```bash
./venv/bin/python -m pytest
```

After a `requirements-dev.txt` change:

```bash
cd services/auth && ./venv/bin/pip install -r requirements-dev.txt
```

## Running tests

All suites in sequence (creates `study_hub_test` if missing):

```bash
bash run-tests.sh
```

One service at a time:

```bash
cd services/auth && ./venv/bin/python -m pytest -q
```

Postgres must be up. If you only want the database and not the full app stack:

```bash
docker compose up -d postgres
```

## Accessing the database directly

Interactive session:

```bash
docker exec -it mp-project-study-hub-postgres-1 psql -U study_hub -d study_hub
```

Useful commands once inside:

```sql
\dn                    -- list schemas (auth, items, board, connectors — schema-per-service)
\dt auth.*             -- list tables in one schema
\d auth.users          -- describe a table's columns/types/constraints
SELECT * FROM auth.users LIMIT 10;
\q                     -- exit
```

One-off query without entering the interactive shell:

```bash
docker exec mp-project-study-hub-postgres-1 psql -U study_hub -d study_hub -c "SELECT source, count(*) FROM items.items GROUP BY source;"
```

GUI clients (DBeaver, TablePlus, pgAdmin) can connect directly too — Postgres's port is exposed to the host:
- Host: `localhost`, Port: `5432`, Database: `study_hub`
- User: `study_hub` / Password: `study_hub_dev_password` (from `docker-compose.yml`)

## Evening: shutting down

```bash
docker compose down
```

Stops and removes the containers but **keeps your data** (the `postgres_data` volume persists).
It also tears down in reverse dependency order, so Postgres shuts down last and exits cleanly —
which the Docker Desktop stop buttons do not guarantee.

⚠️ Never run **`docker compose down -v`** as a normal shutdown command — the `-v` deletes the volume too,
wiping the actual dev database. That's only for deliberately testing the fresh-clone bootstrap story from scratch.

### Windows-side cleanup (weekly, or when disk gets tight)

WSL and Docker virtual disks grow as you work and **never shrink on their own** — not on reboot,
not after `docker system prune`. Reclaiming that space needs compaction, from an **elevated
PowerShell on Windows**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\DELL\Scripts\Invoke-EndOfDayCompaction.ps1"
```

Add `-SetSparse` the **first time only** — it marks the WSL disks sparse so they self-shrink
from then on, which makes this largely unnecessary afterwards.

**Close VS Code before running it.** Its WSL extension restarts Ubuntu the moment the distro
shuts down, which would undo the shutdown and make compaction unsafe. The script refuses to run
while an editor is open rather than risking a corrupted VHDX.

Most of the recovery comes from `wsl --shutdown` itself: WSL2 and Docker each allocate a swap
VHDX that is **deleted** when the distros stop — typically ~10 GB combined. Compaction adds little
on top, and a reboot adds nothing: Windows sizes `pagefile.sys` from recent peak commit usage, so
it rebuilds at the same size rather than shrinking. Reboot if you want to, but not for disk space.

Related scripts on the Windows side:

| Script | When |
|---|---|
| `Invoke-DiskMaintenance.ps1` | weekly report; `-Clean` clears rebuildable caches |
| `Invoke-EndOfDayCompaction.ps1` | compact WSL/Docker disks (elevated, VS Code closed) |
| `Rescue-IdmStalledDownload.ps1` | unrelated to this project — rescues stalled IDM downloads |
