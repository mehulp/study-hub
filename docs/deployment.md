# Deployment — Railway + Cloudflare

How the live deployment is actually wired together: two platforms, one project each,
connected by a handful of environment variables. This is a reference for redoing or
debugging the setup — the *why* behind each decision lives in the Decision Log
(`study-hub-architecture.md`, #87–#93); this doc is the *how*.

**Live URLs:**
- Frontend: `https://study-hub.mehul-patankar.workers.dev` (Cloudflare Workers)
- Backend entry point: `https://gateway-production-539a.up.railway.app` (Railway)

## Architecture at a glance

```
Browser
  │
  ▼
Cloudflare Workers (web/ — static React build + SPA routing)
  │  every API call goes to VITE_GATEWAY_URL, baked in at build time
  ▼
Railway: gateway (public domain, the only Railway service that needs one)
  │  every other service talks over Railway's private network only
  ├──▶ auth        (RS256 JWT issuing/verification)
  ├──▶ items       (resources, tags, learning plans)
  ├──▶ board       (sharing/boards, calls auth + items itself)
  ├──▶ connectors  (Twitter OAuth — dormant, Decision #61)
  └──▶ Postgres    (one instance, schema-per-service)
```

Five Railway services + one Postgres, one Cloudflare Workers project. Nothing else.

## Part A — Railway project setup

One Railway **project** holds all 6 resources (5 services + Postgres) — not one project
per service. Free tier caps out around 4-5 resources; this setup needs the Hobby plan
($5/mo + usage) to fit all 6.

For each of the 5 services (`auth`, `items`, `board`, `connectors`, `gateway`):

1. **New Service → GitHub Repo** → select `mehulp/study-hub`.
2. **Settings → Source**: set **Root Directory** to `services/<name>` (e.g. `services/auth`)
   — this is a monorepo, Railway needs to know which subdirectory has that service's own
   `Dockerfile`. It auto-detects the Dockerfile once Root Directory is set correctly.
3. **Settings → Deploy**: leave **Custom Start Command** blank — the Dockerfile's own `CMD`
   (`./entrypoint.sh` for `auth`, `alembic upgrade head && uvicorn ...` for the rest) is
   what should run. A stray value here silently overrides the Dockerfile and was the
   actual root cause of one real outage during setup (see Part C's troubleshooting note).
4. **Settings → Deploy**: turn **Sleep Application** off. These services depend on each
   other synchronously — a sleeping downstream service breaks any request through it.
5. Add a **Postgres** resource once (New → Database → PostgreSQL) — shared by all 5
   services via schema-per-service, exactly like local `docker-compose.yml`.

## Part B — Environment variables per service

Railway's Postgres plugin exposes `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD`/`PGDATABASE`
automatically — build `DATABASE_URL` from those via `${{Postgres.PGUSER}}` etc.
reference syntax, don't hardcode.

**Cross-service URLs are the single biggest gotcha.** `docker-compose.yml` uses bare
Docker service names (`http://auth:8001`) — those do **not** resolve on Railway. Use
Railway's private-networking reference variable instead, which is guaranteed correct
because Railway substitutes its own real value at deploy time:

```
http://${{auth.RAILWAY_PRIVATE_DOMAIN}}:8001
```

| Service | Variables |
|---|---|
| `auth` | `DATABASE_URL` (from Postgres refs), `JWT_PRIVATE_KEY_PEM_B64`, `JWT_PUBLIC_KEY_PEM_B64` (see Part C) |
| `items` | `DATABASE_URL`, `AUTH_SERVICE_URL=http://${{auth.RAILWAY_PRIVATE_DOMAIN}}:8001` |
| `board` | `DATABASE_URL`, `AUTH_SERVICE_URL=http://${{auth.RAILWAY_PRIVATE_DOMAIN}}:8001`, `ITEMS_SERVICE_URL=http://${{items.RAILWAY_PRIVATE_DOMAIN}}:8002` |
| `connectors` | `DATABASE_URL`, `AUTH_SERVICE_URL=...`, `ITEMS_SERVICE_URL=...`, `OAUTH_CLIENT_ID=connectors-service`, `OAUTH_CLIENT_SECRET` (rotate via `services/auth/create_oauth_client.py`), `TWITTER_CLIENT_ID=`, `TWITTER_CLIENT_SECRET=`, `TWITTER_REDIRECT_URI=` (**present with empty values, not omitted** — see gotcha below) |
| `gateway` | `AUTH_SERVICE_URL`, `ITEMS_SERVICE_URL`, `BOARD_SERVICE_URL=http://${{board.RAILWAY_PRIVATE_DOMAIN}}:8003`, `CONNECTORS_SERVICE_URL=http://${{connectors.RAILWAY_PRIVATE_DOMAIN}}:8004`, `CORS_ALLOWED_ORIGINS=<Cloudflare Workers URL from Part D>` |

**Gotcha — `connectors`' blank Twitter variables.** `twitter_client.py` reads
`os.environ["TWITTER_CLIENT_ID"]` unconditionally at import time. `os.environ[...]`
raises `KeyError` if the key is **absent**, not just falsy-on-empty — local dev never
hits this because the root `.env` always defines the key (blank). On Railway, add all
three `TWITTER_CLIENT_*` variables with empty values explicitly; don't just skip them.

## Part C — Auth's JWT keys

`services/auth/private_key.pem`/`public_key.pem` are real, `.gitignore`'d key material —
present locally only because they're on disk and get picked up by `COPY . .`. A git-clone
deploy never has them. `services/auth/entrypoint.sh` writes them from env vars, **only if
the files don't already exist** (so local `docker compose up` is untouched):

```sh
if [ ! -f private_key.pem ] && [ -n "$JWT_PRIVATE_KEY_PEM_B64" ]; then
  echo "$JWT_PRIVATE_KEY_PEM_B64" | base64 -d > private_key.pem
fi
```

**Gotcha — use base64, not raw PEM text.** A raw multi-line PEM pasted into Railway's
single-line variable input loses its newlines, and PEM parsing depends on that line
structure — this failed live with `ValueError: ... MalformedFraming`. Generate the values
with:
```
base64 -w0 services/auth/private_key.pem
base64 -w0 services/auth/public_key.pem
```
and set them as `JWT_PRIVATE_KEY_PEM_B64` / `JWT_PUBLIC_KEY_PEM_B64` on `auth` only.

**Troubleshooting note (real incident):** if `auth`'s logs show migrations succeeding
followed immediately by `FileNotFoundError: ... private_key.pem` (not a PEM parse error),
the env vars above are correctly named but not actually reaching the container — check
`auth`'s Settings → Deploy → **Custom Start Command** isn't overriding the Dockerfile's
`CMD`. This exact failure happened during setup because that field had a stray value in
it, silently bypassing `entrypoint.sh` (and its key-writing logic) entirely.

## Part D — Frontend on Cloudflare Workers

Cloudflare has moved static-asset deploys from classic Pages (dashboard-configured output
directory) to the unified Workers platform — a committed config file replaces the old
dashboard fields. `web/wrangler.jsonc`:

```jsonc
{
  "name": "study-hub",
  "compatibility_date": "2026-09-11",
  "assets": {
    "directory": "./dist",
    "not_found_handling": "single-page-application"
  }
}
```

`not_found_handling: "single-page-application"` matters — without it, a direct load or
refresh of a client-side route like `/boards` 404s instead of serving `index.html`.

Setup, at [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → Create:
1. Connect to Git → select the `study-hub` repo.
2. **Root directory: `web`** (this is a monorepo — `package.json` isn't at the repo root;
   the build fails with `npm error enoent ... package.json` without this).
3. Build command: `npm run build` (already correct by default).
4. Deploy command: `npx wrangler deploy` (already correct by default — reads
   `wrangler.jsonc`).
5. Settings → Variables and Secrets → add `VITE_GATEWAY_URL` = the full Railway gateway
   URL **including `https://`** (a bare hostname resolves as a relative path against the
   Worker's own origin, producing a broken combined URL). This is a **build-time** Vite
   variable — setting it after a deploy has no effect until the next rebuild.
6. Settings → Domains and Routes → the `workers.dev` route may show as **Disabled** by
   default — enable it, or the site won't be reachable at all.

## Part E — Closing the loop

Once the Cloudflare URL is live, set it as `CORS_ALLOWED_ORIGINS` on Railway's `gateway`
and redeploy `gateway`. Until this is done, every request from the browser fails CORS.

## Seeding real demo data onto a deployed target

`scripts/seed_demo_data.py` talks to Items/Board/Auth purely through the real Gateway
API — never the database directly — so it already works against any deploy, not just
`localhost`. Three env vars make it fully target-agnostic (each falls back to the
original local-dev behavior when unset):

```
GATEWAY_URL=https://<gateway-domain>       # default: http://localhost:8000
OWNER_PASSWORD=<existing password>         # default: fresh random
RECEIVER_PASSWORD=<existing password>      # default: fresh random
```

`OWNER_PASSWORD`/`RECEIVER_PASSWORD` only matter if those accounts already exist on the
target (e.g. you signed up manually to smoke-test login first) — the script's signup call
already tolerates a 409 (account exists) and falls through to login, but login needs the
*real* password, not a freshly generated one.

```
GATEWAY_URL="https://gateway-production-539a.up.railway.app" \
OWNER_PASSWORD="..." \
python3 scripts/seed_demo_data.py
```

## Ongoing costs

- **Cloudflare Workers**: effectively $0 at this traffic level (well within the free tier).
- **Railway**: usage-based on the Hobby plan (~$5-15/mo realistic for 5 small always-on
  FastAPI services + Postgres at idle-to-light personal use). Leaving everything running
  is fine — idle services cost close to nothing; there's no need to stop anything between
  work sessions.
