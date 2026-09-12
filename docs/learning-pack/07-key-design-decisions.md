# Study Hub — Key Design Decisions

*Part of the [learning pack](./). Previous: [06-deployment-and-runtime.md](06-deployment-and-runtime.md). Next: [08-interview-project-walkthrough.md](08-interview-project-walkthrough.md).*

The 15 decisions most worth being able to defend cold. Full reasoning and verification
detail for every one of these lives in `docs/study-hub-architecture.md`'s Decision Log —
this is the skim-right-before-an-interview version. Decision numbers reference that log.

### 1. Real microservices, not a modular monolith

**Problem:** A modular monolith would be faster to build and fully sufficient for this
app's actual scale. **Options:** (a) disciplined internal module boundaries, one
deployable; (b) genuinely separate services. **Decision:** (b) — five real services behind
a Gateway. **Why:** the explicit goal is hands-on fluency with real network boundaries,
independent deployability, and service-to-service auth — none of which a monolith can
teach, because none of it exists without a real process/network boundary. **Trade-off:**
meaningfully more operational overhead than a single-user app structurally needs, accepted
on purpose.

### 2. Schema-per-service Postgres (Decision #13)

**Problem:** true database-per-service is the textbook pattern but heavier to operate
locally than a learning project needs. **Options:** (a) fully separate Postgres instances;
(b) one shared schema, no separation; (c) one instance, one schema per service. **Decision:**
(c). **Why:** keeps the discipline that matters (no service reaches into another's tables)
without multiplying database containers — a real pattern used in production systems too,
not just a shortcut. **Trade-off:** enforced by code convention, not by the infrastructure
itself; nothing physically stops a cross-schema join the way separate instances would.

### 3. No cross-service foreign keys (Decision #14)

**Problem:** given schema-per-service, should a table ever FK into another service's
schema? **Decision:** never — cross-schema references are plain UUID columns, validated
once by application code at write time, not database-enforced. **Why:** a real FK across
schemas would silently recreate the coupling schema-per-service exists to avoid. **Trade-off:**
referential integrity across the boundary is only as good as the one validation call that
happened at write time — see Decision #37/#94 below for where this costs something real.

### 4. RS256 over HS256 for JWTs (Decision #24)

**Problem:** symmetric (HS256) signing is simpler — one shared secret. **Decision:**
asymmetric RS256 — Auth holds the private key, every verifier holds only the public key.
**Why:** a shared HS256 secret would give every verifying service forgery capability, not
just verification. RS256 also matches how real IdPs operate (Okta, Auth0: private key held
by the issuer alone). **Trade-off:** a real key-pair generation/rotation story HS256
wouldn't need.

### 5. Gateway validates, but every service re-verifies anyway (Decision #30)

**Problem:** Gateway already checks the JWT — should downstream services just trust that?
**Decision:** no — every service independently re-verifies the same token. **Why:**
trusting a request because of where it came from is exactly what Zero Trust rejects; no
single service's security should depend on every other piece being configured correctly.
**Trade-off:** duplicated verification logic and a little repeated work, every request.

### 6. Refresh-token rotation with reuse detection (Decisions #26/#28)

**Problem:** a long-lived refresh token is a bigger theft target than a short-lived access
token. **Decision:** every refresh issues a brand-new token and permanently revokes the
old one; if an already-revoked (rotated-away) token is ever presented again, every active
token for that user is revoked, forcing full re-login. **Why:** rotation alone only limits
a theft window; reuse detection is what turns "an old token showed up" into an actionable
signal, since a legitimate client would never hold a stale one. **Trade-off:** one more
database write on every single refresh call.

### 7. Service identity via OAuth2 client credentials (Decision #41)

**Problem:** a background job (Connectors) needs to act on a user's behalf with nobody
logged in. **Options:** (a) have it hold and refresh a borrowed user session; (b) its own
distinct machine identity. **Decision:** (b). **Why:** a service impersonating a user
session blurs who actually did what; a distinct credential matches how real systems
authenticate machine callers. **Trade-off:** a second, different credential type to build,
store, and eventually rotate.

### 8. Board stores an item snapshot instead of a live Items call (Decisions #37/#94)

**Problem:** the original design had Board call Items live on every view. **Decision:**
copy the display fields onto Board's own row once, at add-time. **Why:** Items only ever
answers "what are *your* items" — correct for the owner, but breaks the moment someone the
board was *shared with* tries to view it, since they're not asking about their own items.
**Trade-off:** a real staleness gap — if the source item's title/tags change later, the
board's copy doesn't know. **Concrete lesson from later hardening it (Decision #94):** the
snapshot was originally built before tags existed, so it never captured them — when a
"save shared item to my library" feature shipped and produced tag-less copies, the fix was
widening the snapshot to include tags, not (as first proposed) making tags a global,
cross-user concept, which would have solved the wrong problem.

### 9. Learning Plans live inside Items, not a new service (Decision #85)

**Problem:** Plans is a self-contained feature — does it deserve its own service, the way
Board did? **Decision:** no — new tables in Items' own schema. **Why:** Plans has no
sharing, no RBAC beyond plain ownership, and no independent scaling story — none of the
criteria that actually justified Board becoming its own service. **Concrete payoff:**
`PlanItem.item_id` is a real foreign key (same schema), unlike Board's soft reference —
Postgres itself enforces it, for free, specifically because this call was made.

### 10. No real email delivery — manual invite links (Decision #38, revisited and declined)

**Problem:** sharing currently requires manually copying a link to send yourself; real
transactional email (via Resend) was designed in full detail later, including revisiting
whether to validate the invite against the invited email. **Decision:** keep manual
links. **Why:** the existing signup-from-invite flow already supports "share the link
however you want" with zero new code; adding a real email provider is new infrastructure
for a workflow that already works, on a project explicitly scoped as personal. **Trade-off:**
a genuinely less-polished share flow than a real product would ship.

### 11. Manually-entered resources over automated connectors (Decisions #60/#61)

**Problem:** the project's original shape (bookmarks-hub) was built around automated
capture (browser extension, Twitter API). **Decision:** manual entry is the primary path;
both connectors are kept as real, working, demonstrated code but never wired into the live
product. **Why:** manual entry with tags is a more honest match for how the product is
actually used (curated study resources, not a bookmark firehose), and Twitter's bookmark
API has a real per-read cost that authorization alone doesn't. **Trade-off:** the
connectors' engineering value is real but currently unexercised — a deliberate, named
trade-off, not a wasted effort.

### 12. Client-side search/filtering over a search backend

**Problem:** should search/tag-filtering/stats be server-side queries as data grows?
**Decision:** stay client-side — the full item list is already fetched on page load; every
filter/search/stat is computed in the browser over data already in memory. **Why:** at
personal scale (tens to low hundreds of resources), a "search API" would just move an
already-trivial in-memory filter over the network for no behavioral gain. **Trade-off:**
recomputed on every relevant render rather than cached/paginated server-side — a real limit
if the dataset ever grows past what's reasonable to fetch whole (the named trigger for
finally introducing Postgres full-text search).

### 13. Deployment platform: Railway + Cloudflare Workers (Decisions #87–#91)

**Problem:** where to actually deploy five services + Postgres + a static frontend.
**Options considered and ruled out with current facts, not assumptions:** AWS App Runner
(no longer accepting new customers), Fly.io (no free tier for new accounts), Render (free
tier can't cover 5 always-on services), DigitalOcean (~$25/mo minimum before a database).
**Decision:** Railway (backend, usage-based, reads the existing Compose-shaped services
directly) + Cloudflare Workers (frontend, effectively free at this scale). **Trade-off:**
real, live platform gotchas paid for during setup — Railway's private-networking reference
variables vs. Compose hostnames, Cloudflare's Pages→Workers migration requiring a committed
config file instead of dashboard settings.

### 14. Widening the board snapshot instead of "making tags global" (Decision #94)

**Problem:** a receiver copying a shared board item into their own library got a
tag-less copy — tags never existed when Board's snapshot was designed. **First
instinct floated:** make tags a shared, cross-user/global concept. **Decision:** just
widen `board_items` to also snapshot `tags`, same pattern as title/url. **Why:** tags were
never actually user-scoped to begin with (no registry, no ownership concept) — the real
bug was a missing column, not a scoping problem. "Global tags" would have been a
materially bigger, different feature solving a problem that didn't exist, while leaving
the real one (the missing column) unfixed. **The lesson:** the first framing of a bug isn't
always the right diagnosis — worth tracing to the actual root cause before reaching for the
architecturally bigger fix.

### 15. Declining to make Board show live (non-stale) data (Decision #93)

**Problem:** Board's snapshot (see #8 above) can go stale — worth fixing properly with a
new service-to-service read path? **Decision:** no, explicitly declined. **Why:** a
teammate's own catch during the design discussion — fixing staleness doesn't fix the actual
felt problem, since a viewer still has no way to *know* a board changed at all without
revisiting it. That's a materially bigger feature (some kind of "what changed since I last
looked" tracking) than the staleness fix alone, for a gap that's genuinely minor at personal
scale. **The lesson:** recognizing when a proposed fix doesn't actually solve the real
problem is itself a design decision worth stating out loud, not just building the smaller
thing anyway.
