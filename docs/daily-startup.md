# Daily Startup — Quick Reference

The whole stack is containerized (Decision #35), so daily startup is one command, not a per-service manual routine.

**Only one of bookmarks-hub / mp-project-study-hub runs at a time.** `mp-project-study-hub`
(`/home/mehul/projects/mp-project-study-hub`) is a separate project cloned from this one, deliberately sharing
the same ports rather than each getting its own — simpler, and easier to shut down, at the cost of never
running both simultaneously. `start-dev.sh` in both projects checks for this and refuses to start if the
other one's containers are already up, rather than failing with a confusing Docker port-bind error.

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
