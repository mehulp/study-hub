# Bookmarks Hub — Architecture & Decision Log

**Purpose of this doc:** A living record of every design decision made while building this project, and why. This is the primary artifact — the goal is to be able to defend each decision in an interview, not just to have working code. Update this doc every time a real decision is made, in Claude chat or in Claude Code.

**Project goal:** A personal, learning-focused project to rebuild hands-on system design fluency (architecture, microservices, auth/authz, RBAC, basic UI) ahead of Senior EM / Director interviews. Not a coding-skill exercise — the point is being able to explain and defend every architectural choice.

---

## Problem Scope

A personal "bookmarks hub" — a single place to view bookmarks saved across different sources (browser bookmarks first, Twitter/X later), displayed as tiles, organized by source, with the ability to share a curated board with another person under real Owner/Editor/Viewer permissions.

**In scope (in build order):**
1. Browser bookmarks (Chrome + Firefox, via a shared WebExtensions-based browser extension) — free, no third-party API cost
2. Tile dashboard, organized by source
3. Sharing with real RBAC (Owner / Editor / Viewer)
4. Twitter/X bookmarks (OAuth2 + PKCE) — added last, since it requires a paid X developer account

**Explicitly out of scope:** CVE/vulnerability tracking (dropped — kept the personal project personal, separate from work-adjacent content).

## How We're Building This (Process)

1. **User journeys** — what actually happens, step by step, from the user's point of view
2. **Domain model** — the core entities/nouns that fall out of those journeys
3. **API & service boundaries** — which service owns which verb, who talks to whom
4. **Data schema** — tables that store the state, designed only after 1–3 are settled
5. **Build: backend, then UI** — implement against the contract already defined
6. **Test & review** — verify, then loop findings back into step 1

Working style: step by step, one decision at a time. Each decision gets explained (what we chose, what the alternatives were, why) before moving to the next. No large chunks of generated code without understanding checkpoints.

```mermaid
flowchart TD
    A["1. User journeys<br/>What happens, step by step"] --> B["2. Domain model<br/>Core entities from the journeys"]
    B --> C["3. API & service boundaries<br/>Who talks to whom"]
    C --> D["4. Data schema<br/>Tables that store the state"]
    D --> E["5. Build: backend, then UI<br/>Implement against the contract"]
    E --> F["6. Test & review<br/>Verify, then iterate"]
    F -.->|findings loop back| A
```

## Hosting / Environment Decisions

- **Build phase:** entirely local via Docker Compose. No cost, fast iteration, no vendor quirks to learn alongside the architecture itself.
- **Twitter OAuth testing:** will need a public HTTPS callback — use a tunnel tool (ngrok / Cloudflare Tunnel) rather than deploying early.
- **Live demo deploy (near interview time, optional):** Render, using a paid Starter tier ($7/mo) or accepting cold starts on the free tier — avoiding Render's free Postgres, which auto-deletes after 30 days.
- **Tooling:** Claude Code (VS Code) for implementation once set up on the personal laptop (setup pending — previous integration was on the now-departing office Mac). Architecture/decision conversations continue here in Claude chat.

## Data Model (early sketch — will be refined at Step 4)

`Users`, `Boards`, `BoardItems` (normalized: title, url, thumbnail, source, tags, saved_at), `BoardShares` (board_id, user_id, role: Owner/Editor/Viewer)

## Open Design Questions

- Where should RBAC be enforced — gateway-level only, or also independently per service? (Deliberately left open — this is a documented trade-off, not a gap.)

## Concepts Learned (for interview articulation)

- **Entity vs. code distinction:** something belongs in the data model (an entity/table) if a background process needs to read it again later, without the user present. If it only matters in the instant it's happening, it's code, not data. Example: the OAuth handshake with Twitter is code (runs once); the access token it produces is data (must persist so the ingestion connector can keep working weeks later without re-authorization) — hence `Connection` is an entity, not just logic.
- **Zero Trust Architecture (NIST SP 800-207):** never trust a service-to-service call just because of network location ("it's inside our VPC" is not a control). Every internal call gets authenticated and authorized independently. In production this is usually mTLS via a service mesh (Istio/Linkerd) with SPIFFE/SPIRE giving each workload a cryptographic identity, plus a policy engine (OPA) for authorization — full audit trail of real service identity, not just "someone with the key." This project approximates the same identity principle (short-lived, per-service, verifiable tokens) via OAuth2 client-credentials flow, without the mesh infrastructure — a deliberate scope trade-off worth stating explicitly as "how this scales at a real company" in an interview.

## Step 2: Domain Model — DRAFT (pending further discussion)

Entities identified from the four journeys, and why each earns its own table rather than being folded into another:

- **User** — the account table. Appears in two different relationships (the owner who creates boards/connections, and a recipient who receives access) but it's the same entity both times — the relationship differs, not the underlying thing.
- **Connection** — one authorized link to a source (Twitter OAuth tokens + expiry, or the browser extension's registration + last-synced time). Needs its own entity because a background ingestion process reads it again on every future run.
- **Item** — the normalized shape of "one bookmark," regardless of source (title, url, source, folder path if applicable, preview data, saved_at). Lets one UI component render items from any source, and is what a Board actually references.
- **Board** — a purpose-built sharing container, created only when items are explicitly selected and shared. Not the same as the default Twitter/Browser dashboard views, which are just "all your own items, filtered by source" — no Board involved there, since the owner always sees everything directly.
- **Access Grant** — conceptually "a board grants a role to a user." Will split into two real states at schema time (Step 4): a pending invite keyed by email (with an expiring token, before the recipient has an account) and a settled share keyed by user_id once they've signed up.

```mermaid
erDiagram
  USER ||--o{ CONNECTION : authorizes
  CONNECTION ||--o{ ITEM : produces
  USER ||--o{ BOARD : creates
  BOARD }o--o{ ITEM : contains
  BOARD ||--o{ ACCESS_GRANT : "shared via"
  ACCESS_GRANT }o--|| USER : "grants role to"
```

Relationships in plain language:
`User` authorizes many `Connection`s → each `Connection` produces many `Item`s → `User` creates many `Board`s → `Board` contains many `Item`s (many-to-many) → `Board` is shared via many `Access Grant`s → each `Access Grant` grants a role to one `User` (the recipient).

No columns/types yet — that's Step 4 (data schema), after API/service boundaries (Step 3) are settled.

## Step 3: API & Service Boundaries — DRAFT (pending further discussion)

Four services, each with a single data owner:

- **Gateway** — owns no data. Validates the JWT once per request, attaches user identity, routes to the right service. Coarse-grained auth check only ("is this a valid logged-in user") — fine-grained role checks (can *this* user edit *this* board) live inside Board service, since only it knows the role for that specific board.
- **Auth service** — owns `User`. Verbs: signup, login, issue/refresh JWT.
- **Items service** — owns `Item`. Verbs: ingest (write a new normalized item — called by connectors), list/get items (called by the UI directly, and by Board service when composing a board view).
- **Connectors** (Twitter, Browser) — own `Connection`. Verbs: authorize, fetch/sync from the external source, normalize, then call Items service's ingest endpoint. Connectors do not store `Item` themselves — they're workers, not data owners, which keeps a single source of truth for items regardless of source.
- **Board service** — owns `Board`, the Board↔Item join, and `Access Grant`. Verbs: create board, add/remove items, invite, list board contents (composing item details from Items service — see Decision #11).

```mermaid
flowchart TD
    UI[Web UI] --> GW[Gateway<br/>validates JWT, routes]
    GW --> AUTH[Auth Service<br/>owns User, sessions]
    GW --> ITEMS[Items Service<br/>owns Item catalog, all sources]
    GW --> BOARD[Board Service<br/>owns Board, sharing, access]
    CONN[Connectors<br/>Twitter + Browser ingestion] -->|ingest new items| ITEMS
    BOARD -->|reads item details, with fallback| ITEMS
```

**Internal service-to-service auth (resolved):** OAuth2 client-credentials flow — see Decision #12.

## Step 4: Data Schema — DRAFT (pending further discussion)

**Data separation:** one Postgres instance, one schema per service (see Decision #13). **FK rule:** real foreign keys within a service's own schema; cross-schema references are plain UUID columns validated by application code, never a database-level FK (see Decision #14).

### `auth` schema
- **users**: id (uuid, PK), email (unique, not null), password_hash, created_at, updated_at

### `connectors` schema
- **connections**: id (uuid, PK), owner_user_id (uuid, soft ref → auth.users), type (`twitter` | `browser_chrome` | `browser_firefox`), auth_token (browser push auth, nullable), oauth_access_token / oauth_refresh_token / token_expires_at (Twitter only, nullable), last_synced_at, created_at
  - *Design note: one table with nullable type-specific columns rather than separate tables per connector type — simpler for v1, at the cost of some always-null columns depending on type.*

### `items` schema
- **items**: id (uuid, PK), owner_user_id (uuid, soft ref → auth.users), source (`twitter` | `chrome` | `firefox`), external_id (source's own bookmark ID), title, url, folder_path (nullable — browser only), preview_text / preview_media_url (nullable — Twitter), favicon_url (nullable — browser), saved_at (when bookmarked at the source), created_at (when ingested)
  - **Unique constraint:** `(owner_user_id, source, external_id)` — enables idempotent sync (diff, not full re-import) by letting the database reject duplicate ingests.

### `board` schema
- **boards**: id (uuid, PK), owner_user_id (uuid, soft ref → auth.users), name, created_at
- **board_items** (many-to-many join): board_id (real FK → boards.id, same schema), item_id (uuid, soft ref → items.items), added_at — composite PK (board_id, item_id)
- **access_grants**: id (uuid, PK), board_id (real FK → boards.id, same schema), invited_email, user_id (nullable, soft ref → auth.users — filled in once accepted), role (`viewer` | `editor`), invite_token (unique, signed), invite_token_expires_at, status (`pending` | `accepted`), created_at, accepted_at
  - *Design note: one table models both states of "Access Grant" from Step 2 (pending-by-email, settled-by-user_id) via nullable `user_id` + `status`, rather than two separate tables — the pending→accepted transition is a single row update.*
  - *FK note: `board_id` is a real FK (same-schema, Board service owns both); `user_id` is a soft reference (crosses into `auth` schema — see Decision #14).*

## Future Extensions / Backlog (deliberately out of v1 — captured here so nothing gets lost)

- **Books-read module**: track books read, with personal summaries/notes. Different in kind from the Twitter/Browser connectors — this needs an actual content *editor* (writing original text), not just an ingestion pipeline pulling from an external source. Will likely need its own entity (e.g. `ReadingEntries`: title, author, summary body, rating, date) and a text-editing UI, not a tile-preview UI. Worth revisiting whether "Board" stays generic enough to hold this, or whether it becomes its own module — decide when we get here.
- **Editor role at invite time** (see Decision #10) — role picker deferred, hardcoded Viewer for v1.
- **Add selection to an existing shared board** (see Decision #9) — deferred, v1 always creates a new board.
- **Google Sign-In as an additional login method** (see Decision #6) — deferred, own auth built first.
- **Real-time live sync + in-app alerts**: e.g. bookmarking a tweet in another tab should show up automatically with a notification, without a page refresh. Undecided whether this belongs in v1. Technical nuance worth remembering: browser bookmarks *can* genuinely be real-time (the extension can listen to native events like `chrome.bookmarks.onCreated` and push instantly), but Twitter *cannot* — X's API has no bookmark webhook, so any "live" Twitter updates would really be periodic polling made to look real-time, not a true push. Would also need a push channel to the open browser tab (WebSocket or Server-Sent Events) to deliver the alert.

---

## Decision Log

| # | Decision | Alternatives Considered | Rationale |
|---|----------|--------------------------|-----------|
| 1 | Personal bookmarks hub (browser bookmarks + Twitter, plugin-style connectors) instead of a compliance/CVE-focused SaaS | CVE/vulnerability tracker SaaS (multi-tenant) | Personal project stays authentically personal; connector/plugin pattern still gives strong microservices story |
| 2 | RBAC via a real (small) sharing feature — Owner/Editor/Viewer on boards | Leave RBAC as a design-only talking point | Real enforced code is more defensible in interviews than a stub |
| 3 | Browser bookmarks (Chrome + Firefox via extension) built before Twitter | Twitter first | Free, no developer account/approval friction, proves the pipeline end-to-end before spending money |
| 4 | CVE tracking dropped entirely from scope | Keep CVE as a later "branch" | Kept the project focused and personal |
| 5 | Local Docker Compose for build phase; cloud deploy only near the end, if at all | Deploy early to Railway/Fly.io | No free tiers left on those platforms; local-first avoids cost and cold-start noise while learning |
| 6 | Build own auth first (email/password, self-managed sessions); add Google Sign-In later as an optional additional sign-in method | Start with Google OAuth as primary login | Own auth teaches password hashing, session/JWT design, and invalidation — skills OAuth doesn't touch. Google OAuth would be redundant right now since the Twitter connector already requires building OAuth2+PKCE from scratch later. |
| 7 | Dashboard shows two top-level blocks: Twitter and Browser Bookmarks. Browser Bookmarks expands into Chrome/Firefox sub-folders, each preserving that browser's native folder structure (Bookmarks Bar, Other, custom folders). Twitter is a flat list (no folder concept). | Merge Chrome+Firefox into one flat block; or three flat top-level blocks | Chrome and Firefox are separate, unsynced bookmark stores (Chrome Sync uses Google account, Firefox Sync uses a separate Mozilla account — not the same data). Nesting reflects the real structure without losing it. |
| 8 | Source connection (browser extension install, Twitter OAuth) is a one-time owner/developer setup step, not a polished repeatable user-facing "Connect" flow with empty states | Build a general-purpose connection UX for arbitrary future users | Single-user app for source data; people boards get shared with never connect their own sources, so there's no real audience for a repeatable onboarding flow — building one would be scope for its own sake |
| 9 | Sharing works by selecting tiles (select-all + deselect, or individual picks) and always creates a brand-new board from that selection | Allow adding selection to an existing already-shared board | Keeps v1 simple — one sharing mechanism, no second "add to existing board" flow to design/build yet |
| 10 | Invite by email with a signed, expiring magic link; role is hardcoded to Viewer for v1 (no role picker) | Show a Viewer/Editor picker at invite time | Keeps v1 scope tight; Editor picker deferred to v2 since Viewer alone already proves the RBAC enforcement mechanism |
| 11 | Board service composes item details by calling Items service internally (server-to-server), with a short timeout and graceful fallback — if Items is unreachable, return the board (name, item IDs, sharing info) with affected items flagged "preview_unavailable" rather than failing the whole request | (a) Frontend calls both services and composes client-side, isolating failures naturally; (b) naive backend composition with no fallback | Keeps the frontend simple (one call to Board) while avoiding the cascading-failure trap where an Items outage would otherwise take down board rendering entirely, even though board metadata itself is unaffected |
| 12 | Internal service-to-service auth via OAuth2 client-credentials flow — each internal service has its own client_id/client_secret, requests short-lived JWTs from Auth service, and every internal call carries/verifies that token | (a) Static shared secret across all services; (b) full mTLS via a service mesh (Istio/Linkerd) with SPIFFE/SPIRE workload identity; (c) trusted network / no auth between services | Approximates the real industry pattern (per-service, short-lived, cryptographically verifiable identity — same principle as Zero Trust Architecture, NIST SP 800-207) without building full mesh infrastructure disproportionate to a solo project. Shared secret rejected: no per-service identity, poor audit trail, single point of compromise. Trusted-network rejected: violates Zero Trust, not defensible in a regulated-style story. Full mesh rejected for this project's scale but named explicitly as the production answer. |
| 13 | One Postgres instance, separate schema per service (auth, items, connectors, board) | (a) Fully separate physical database per service; (b) single shared schema, no enforced separation | Approximates the real database-per-service pattern (logical ownership, no cross-service joins) without running four separate Postgres containers locally — a proportionate middle ground several real companies also use in production |
| 14 | Foreign keys are used normally *within* a service's own schema (e.g. `access_grants.board_id` → `boards.id`, both owned by Board service); references that cross into another service's schema (e.g. `access_grants.user_id` → `auth.users.id`) are plain UUID columns validated by application code, never a real FK | Use real FKs everywhere, including cross-schema | A database-per-service split literally couldn't have a cross-database FK — keeping that discipline here (even though everything happens to share one Postgres instance) avoids a coupling the architecture isn't supposed to have. Within one service's own schema, a real FK is correct and desirable — that's what referential integrity is for. |

---

## Step 1: User Journeys — DRAFT (pending discussion)

### Journey 1a: One-time source setup (done once, by you, as owner — not a polished user-facing flow)
1. Install and authorize the browser extension locally, pointed at the app
2. Authorize Twitter via OAuth once, through a simple internal route
3. From this point on, both sources are connected server-side — no "Connect" button, empty state, or retry UX needed, since there's no other audience going through this

### Journey 1b: Everyday login (what happens every time)
1. Open browser, navigate to the app URL (e.g. `mehulsden.xyz` — placeholder)
2. Presented with login — own email/password auth (Google Sign-In deferred to later as an optional method, see Decision #6)
3. After login, dashboard shows two top-level blocks: **Twitter** and **Browser Bookmarks** — both already populated
4. Browser Bookmarks expands into **Chrome** / **Firefox** sub-folders, each preserving that browser's native folder structure (Bookmarks Bar, Other, custom folders) — see Decision #7
5. Twitter is a flat list/tile view (no folder concept)

**Note:** users you later share a board with (see Journey 3/4) never go through Journey 1a — they only ever see boards you've already populated, via Viewer/Editor access.

### Journey 2: Everyday use — browsing
1. **Twitter tab:** default view is tiles, each showing a lightweight preview (tweet text/media — comes free from the API response, no extra fetching)
2. Clicking a Twitter tile opens the original tweet on X in a new tab
3. **Browser tab:** default view is list (not tiles) — bookmark volume makes tiles impractical; each row shows title + URL + favicon only (no full-page preview thumbnails — not worth the extra fetch/caching complexity for a secondary view)
4. Clicking a browser bookmark opens the original URL in a new tab

### Journey 3: Sharing a board
1. Select tiles — either "select all" then deselect unwanted ones, or pick individual tiles one at a time
2. Selection always creates a brand-new board (see Decision #9) — named on the spot
3. Enter the recipient's email address
4. They receive an email with a signed, expiring "authorization" (magic) link
5. Role is hardcoded to Viewer for v1 — no picker (see Decision #10)

### Journey 4: Receiving a shared board
1. Recipient clicks the authorization link in the email
2. If they don't have an account yet, they set one up; if they do, they're logged in directly
3. They land directly on the shared board — no separate "accept invite" step
4. As Viewer: can see all items on the board and open the underlying links (tweets/bookmarked pages) in a new tab, same as owner browsing
5. Cannot add, remove, edit items, or manage sharing on the board
