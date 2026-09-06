# Daily Startup — Quick Reference

The whole stack is containerized (Decision #35), so daily startup is one command, not a per-service manual routine.

Run everything **inside the WSL2 Ubuntu terminal**, not PowerShell. The project lives at
`/home/mehul/projects/bookmarks-hub` (inside WSL). Driving it from Windows would route every
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

## Morning: starting up for the day

```bash
# 0. Start Docker Desktop on Windows first — WSL2 integration needs it running.
#    Wait until the whale icon stops animating.

# 1. In the Ubuntu terminal (or VS Code's integrated terminal):
cd /home/mehul/projects/bookmarks-hub
docker compose up -d
```

Brings up all six services in health-gated dependency order — no manual `alembic upgrade head`,
no separate `uvicorn` commands per service.

If you changed any service's code since last time, rebuild first:

```bash
docker compose up -d --build
```

Then confirm everything's actually healthy:

```bash
docker compose ps
```

All six should show `running` and, where a healthcheck is defined, `(healthy)`. If `auth` is
stuck at `starting`, give it ~10s — its healthcheck has a `start_period`.

### Web frontend (separate from the compose stack)

```bash
cd web && npm run dev          # Vite dev server
```

`node_modules` is already installed; only re-run `npm install` after a `package.json` change.

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

All suites in sequence (creates `bookmarks_hub_test` if missing):

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
docker exec -it bookmarks-hub-postgres-1 psql -U bookmarks_hub -d bookmarks_hub
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
docker exec bookmarks-hub-postgres-1 psql -U bookmarks_hub -d bookmarks_hub -c "SELECT source, count(*) FROM items.items GROUP BY source;"
```

GUI clients (DBeaver, TablePlus, pgAdmin) can connect directly too — Postgres's port is exposed to the host:
- Host: `localhost`, Port: `5432`, Database: `bookmarks_hub`
- User: `bookmarks_hub` / Password: `bookmarks_hub_dev_password` (from `docker-compose.yml`)

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

Then reboot — that recreates `pagefile.sys` at its baseline size, typically recovering several GB
that a day of Docker + WSL + browsers caused it to claim.

Related scripts on the Windows side:

| Script | When |
|---|---|
| `Invoke-DiskMaintenance.ps1` | weekly report; `-Clean` clears rebuildable caches |
| `Invoke-EndOfDayCompaction.ps1` | compact WSL/Docker disks (elevated, VS Code closed) |
| `Rescue-IdmStalledDownload.ps1` | unrelated to this project — rescues stalled IDM downloads |
