# Daily Startup — Quick Reference

The whole stack is containerized (Decision #35), so daily startup is one command, not a per-service manual routine.

## Starting up for the day
```bash
# 1. Make sure Docker Desktop is running (WSL2 integration needs it up first)

# 2. From the project root:
cd /home/mehul/projects/bookmarks-hub
docker compose up -d
```
Brings up Postgres, Auth, Items, and Gateway together, in the correct health-gated order — no manual `alembic upgrade head`, no separate `uvicorn` commands per service.

If you changed any service's code since last time, rebuild first:
```bash
docker compose up -d --build
```

Then confirm everything's actually healthy:
```bash
docker compose ps
```

## Running a service's test suite locally (not through Docker)
Tests still run against your own venv, not inside the containers:
```bash
cd services/auth && ./venv/bin/python -m pytest      # or source venv/bin/activate first, then just `pytest`
cd services/items && ./venv/bin/python -m pytest
cd services/gateway && ./venv/bin/python -m pytest
```
(Postgres needs to be up for these — `docker compose up -d postgres` alone is enough if you only want the DB, not the full app stack.)

## Shutting down at night
```bash
docker compose down
```
Stops and removes the containers but **keeps your data** (the `postgres_data` volume persists).

⚠️ Never run **`docker compose down -v`** as a normal shutdown command — the `-v` deletes the volume too, wiping the actual dev database. That's only for deliberately testing the fresh-clone bootstrap story from scratch.
