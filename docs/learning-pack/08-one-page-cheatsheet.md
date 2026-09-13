# Study Hub — One-Page Cheatsheet

*Part of the [learning pack](./). Previous: [07-key-design-decisions.md](07-key-design-decisions.md). The fastest way to re-orient on the whole system.*

**What it is:** curate study resources (title/URL/notes/tags), organize into Learning
Plans with progress tracking, share a board with a study partner under real RBAC. Built to
rebuild system-design fluency before Senior EM/Director interviews.

## Architecture

```
Browser → Cloudflare Workers (static React) → Gateway (Railway, public)
                                                  ├→ Auth      (User, tokens)
                                                  ├→ Items     (Item, tags, Learning Plans)
                                                  ├→ Board     (Board, sharing, access) → Items (add-time only)
                                                  └→ Connectors (dormant — Twitter OAuth, browser ext.)
All backend services → one Postgres, schema-per-service, private networking on Railway.
```

## Services (one line each)

- **Gateway** — stateless, no DB, routes + coarse auth check, one public entry point
- **Auth** — owns `User`, `RefreshToken`, `OAuthClient`; signs RS256 JWTs
- **Items** — owns `Item`, `ItemTag`, `LearningPlan`, `PlanItem`; the resource catalog
- **Board** — owns `Board`, `BoardItem`, `AccessGrant`; owner/viewer RBAC
- **Connectors** — owns `Connection`; real OAuth2+PKCE code, dormant in the live product

## Database model

One Postgres instance, **schema-per-service**, **no cross-schema FKs** (soft references,
validated in code). Real FK only within a service's own schema — e.g. `PlanItem.item_id`
(same schema as Items) vs. `BoardItem.item_id` (soft ref, crosses into Items' schema).
**Board's one deliberate denormalization**: `BoardItem` snapshots an item's title/url/tags
at add-time, never a live reference — avoids a live cross-service call on every board view,
at the cost of staleness if the source item changes later.

## Auth model

- **RS256** (asymmetric) — Auth alone holds the private key; every service verifies with
  the public key (JWKS) alone. Can verify, can't forge.
- **Access token**: JWT, 15 min, signature-only check, no DB hit.
- **Refresh token**: opaque, 30 days, DB-tracked (`refresh_tokens`), **rotates** on every
  use — reusing an already-rotated token revokes every active token for that user (theft
  signal).
- **Service identity**: OAuth2 client-credentials (`client_id`/`client_secret` → short-lived
  service token, `client_id` claim not `sub`) — how Connectors would authenticate to Items.
- **Password**: Argon2id, timing-safe login (dummy-hash check even for a nonexistent email).

## RBAC

- **Gateway**: coarse — valid logged-in user, yes/no. No concept of boards or roles.
- **Board service**: fine-grained — owner / accepted viewer / nobody, checked fresh per
  request, per board. `Editor` exists in the schema, **never assignable** (no UI picker,
  deliberate scoped-out gap).
- **Invite tokens**: opaque, hashed, not signed, not a JWT. Not checked against the
  invited email at accept time — "anyone with the link," like a Google Docs share.
- **No real email delivery** — invite links shown for manual copy/paste, by design.

## Deployment

- **Backend**: Railway — 5 services + Postgres, private networking
  (`${{service.RAILWAY_PRIVATE_DOMAIN}}`, not bare Compose hostnames), one public domain
  (Gateway).
- **Frontend**: Cloudflare Workers — `wrangler.jsonc`, SPA routing, build-time
  `VITE_GATEWAY_URL`.
- **CI/CD**: GitHub-connected auto-deploy on both platforms, no separate pipeline.
- **Migrations**: `alembic upgrade head` on every container start, before the app boots.
- **Cost**: ~$5-15/mo (Railway), effectively $0 (Cloudflare).

## Top design decisions (see `07-key-design-decisions.md` for the full 15)

1. Real microservices over a monolith — explicitly for the learning, not the scale
2. Schema-per-service, one Postgres — the real-production middle ground
3. RS256 over HS256 — only Auth can forge, everyone else can only verify
4. Gateway checks + every service re-checks — Zero Trust, not just the term
5. Refresh rotation + reuse detection — theft signal, not just an expiry
6. Board snapshots instead of live Items calls — availability over freshness, named cost
7. Learning Plans stayed inside Items — no sharing/RBAC need to justify a new service
8. Declined "make Board live" — the fix wouldn't have solved the real problem (no "what
   changed" signal either way)

## Top trade-offs to name unprompted

- Board's item snapshot can go stale — real, accepted, not hidden
- No caching layer anywhere — nothing in the real workload needs one yet
- Client-side search — right at personal scale, breaks well before 1M users
- No real email delivery — a genuine product gap, a deliberate scope decision
- No centralized observability — the most honest gap to name if asked "what's missing"
