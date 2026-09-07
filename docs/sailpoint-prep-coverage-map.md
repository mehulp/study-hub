# Bookmarks Hub × SailPoint — System Design Revision Notes

**Purpose:** Not a syllabus checklist. This is revision material for the actual question an interview asks: *"tell me about a time you reasoned about X"* — answered with a real decision from this project, not a textbook definition. Kept in the SailPoint/IAM context this prep started from, since identity/access concepts are where this project genuinely overlaps most with that domain.

**What's here:** only concepts this project has actually encountered, or that are directly relevant given where the project is headed next (see `bookmarks-hub-architecture.md`'s Near-Term Direction). Concepts not yet reached (caching, queues, sharding, etc.) are named at the end, not explained — they get added here for real once the project actually builds something that needs them, not before.

**Format per concept:** simple theory → where it shows up in this project → one example from outside it → a handful of things to actually be able to say out loud in an interview.

---

## Authentication vs Authorization

**Simple theory:** Authentication answers "who are you" — proving identity. Authorization answers "what are you allowed to do" — once identity is established, deciding which actions or resources that identity can access. Easy to blur in casual conversation; architecturally, they're two separate questions asked at two separate moments.

**In our project:** Auth service authenticates at login (email + password → a signed token proving "this is user X"). Gateway then asks a coarse authentication question on every request ("is this a valid, unexpired session at all"). Board service separately asks a fine-grained authorization question ("is *this* identity allowed to do *this* thing to *this specific* board") — same token, a completely different check, at a different layer.

**General practical example:** Logging into a banking app authenticates you. Whether you can view a joint account versus only your own is authorization, checked separately, after authentication already succeeded.

**Interview points:**
- Keep them as two distinct architectural questions, always — don't let "logged in" quietly stand in for "allowed to do this."
- HTTP encodes the difference: `401 Unauthorized` really means "authentication failed or missing"; `403 Forbidden` means "authenticated, but not allowed."
- A system can authenticate correctly and still get authorization wrong — e.g. trusting a forwarded identity header instead of independently re-checking.
- Defense in depth means checking both at more than one layer, not trusting an upstream layer's word for it (Zero Trust reasoning — see `bookmarks-hub-architecture.md`'s Concepts Learned section).
- This split is the backbone of what SailPoint/IdentityIQ actually does at enterprise scale: authentication is usually delegated to an IdP (Okta, Azure AD), while SailPoint's own job is almost entirely the authorization side — governing and certifying *what* an already-authenticated identity should be allowed to access.

---

## REST APIs / HTTP basics

**Simple theory:** A style for designing APIs around resources (nouns — "a board," "an item") manipulated via standard HTTP verbs (`GET` read, `POST` create, `PATCH`/`PUT` update, `DELETE` remove), with status codes communicating outcome.

**In our project:** every service exposes plain REST endpoints — `POST /board` creates one, `GET /board/{id}` reads one, `POST /board/{id}/items` adds an item. Status codes are used deliberately: `201` for "created new," `200` for "already existed, here it is" (idempotent ingest — see below), and the *same* `404` used for both "doesn't exist" and "exists but you can't see it," on purpose, to avoid confirming a resource's existence to someone without access to it.

**General practical example:** any typical CRUD backend — a to-do list API, a blog's post API — follows this same resource-plus-verb shape.

**Interview points:**
- Idempotency is verb-specific: `GET`/`PUT`/`DELETE` should be safe to retry; `POST` usually isn't, unless deliberately made idempotent.
- Status codes are part of the contract, not cosmetic — clients make real decisions from them (retry on `5xx`, don't retry on `4xx`).
- Returning an identical `404` for "not found" and "not yours" is a deliberate anti-enumeration pattern, not an oversight.
- A generic, uniform verb model is exactly what lets a reverse-proxy Gateway forward *any* request without understanding the specific resource behind it.

---

## JWT (JSON Web Token)

**Simple theory:** A compact, self-contained, signed token — a header, a payload of claims (like user id and expiry), and a signature. Anyone holding the right verification key can check it's genuine and unexpired without ever calling the issuer back.

**In our project:** Auth issues access tokens as JWTs signed with RS256 (asymmetric — a private key signs, a public key verifies). Gateway and every backend service hold Auth's public key (fetched once via a JWKS-style endpoint, `/.well-known/jwks.json`) and independently verify every token themselves.

**General practical example:** most identity providers (Okta, Auth0, and SailPoint's own IdentityNow) issue JWT access tokens for exactly this reason — verification needs no network round-trip to the issuer.

**Interview points:**
- A JWT is verifiable, not secret — anyone can decode and read the payload; only the signature is protected.
- Asymmetric signing means only the issuer can *mint* valid tokens, while many services can *verify* them — a real least-privilege property, not just crypto trivia.
- A JWT can't be revoked before its own expiry by itself — which is exactly why it's kept short-lived, with revocation handled by a separate mechanism (see next entry).
- Not every token needs to be a JWT: an opaque, database-tracked token is the deliberately *better* choice whenever revocability matters more than stateless, no-lookup verification (this project's refresh tokens and invite tokens are both opaque, on purpose — see below).

---

## Access token vs Refresh token

**Simple theory:** An access token is short-lived and sent on every request to prove identity. A refresh token is longer-lived and used only to obtain a new access token, without re-entering credentials.

**In our project:** access tokens last 15 minutes and are stateless JWTs. Refresh tokens last 30 days, are opaque random strings (not JWTs), hashed and tracked in the database, and are *rotated* on every use — a new one issued, the old one marked revoked. If an already-rotated refresh token is ever presented again, that's treated as a theft signal and every active session for that user is revoked immediately.

**General practical example:** the standard OAuth2 pattern behind essentially every major identity provider — a short-lived bearer credential plus a longer-lived, revocable renewal credential.

**Interview points:**
- Short access-token lifetime limits the blast radius of a leak; the refresh token is what actually needs strong protection, since it's what's long-lived.
- Rotation plus reuse-detection is what makes a stolen refresh token *detectable*, not merely time-limited.
- A stateless JWT refresh token can't be revoked before its own expiry — precisely why this project's are deliberately opaque and DB-tracked instead.
- "Logging out" only means something if there's a real server-side thing to invalidate — a pure stateless-JWT design has no genuine logout, just a client that stops sending the token.

---

## RBAC (Role-Based Access Control)

**Simple theory:** Access decisions are made from a role a user holds for a given resource (Owner, Viewer, Editor…), rather than checking a long list of individual permissions one at a time.

**In our project:** a board has exactly one Owner (its creator) and any number of Viewers (via an accepted invite). Owner can add/remove items and invite others; Viewer can only read. **Editor is a real, reserved value in the schema, but is not currently assignable anywhere** — no role picker exists, invites are hardcoded to Viewer. Worth being precise about: this project has *two* roles genuinely built and enforced, not three.

**General practical example:** Google Docs' Owner / Editor / Commenter / Viewer roles on a shared document are the same pattern at consumer scale.

**Interview points:**
- RBAC checks belong close to the resource that understands the role, not at a generic gateway — this project's fine-grained role check lives in Board service, not Gateway.
- A role isn't just a label — it has to be enforced at *every* relevant endpoint (add, remove, invite), not merely reflected in the UI.
- Be exact about what's actually built vs. merely designed for — a schema anticipating a role is not the same claim as that role being reachable through any real flow.
- RBAC is coarser-grained than full attribute-based access control (ABAC) — sufficient here because the real access question is simple ("owner or not"), not a rich, contextual policy decision.
- RBAC (and its ABAC extension) is the actual theoretical foundation SailPoint IdentityIQ's role mining, role modeling, and access-certification features are built on — this small project is a toy-scale version of the same "who has which role on which resource" question SailPoint answers at enterprise scale.

---

## API Gateway

**Simple theory:** A single front door every external request passes through first, handling cross-cutting concerns (routing, coarse authentication, CORS) once, so individual backend services don't each reimplement them.

**In our project:** Gateway is a generic reverse proxy driven by a routing table (`{path_prefix, target_service}`). It validates a JWT's signature and expiry once per request, then forwards the request unchanged to whichever backend owns that path prefix. It owns no data of its own.

**General practical example:** Kong, Envoy, and AWS API Gateway play this exact role in real production systems — declarative routing configuration, not hand-written glue per endpoint.

**Interview points:**
- A gateway's authentication check is deliberately coarse ("is this a valid session at all") — fine-grained authorization stays with whichever service actually understands the resource.
- A generic, table-driven gateway can onboard a new backend service with zero code changes to the gateway itself — just one new routing-table row.
- A gateway is a natural place to enforce some things uniformly (like CORS) — but it is not a substitute for each service's own independent verification (Zero Trust reasoning — see `bookmarks-hub-architecture.md`'s Concepts Learned section).
- Being stateless (no database) means Gateway can scale out or restart freely with no data-consistency concerns of its own.

---

## Microservices / service boundaries

**Simple theory:** Splitting a system into multiple independently deployable services, each owning a distinct slice of data and responsibility, communicating only over the network — never sharing a database or making an in-process call into another service's internals.

**In our project:** Auth, Items, Board, and Connectors each own their own database schema and business logic. Nothing reaches into another service's tables directly — notably, Board displaying an item's details reads its *own* stored copy rather than reaching into Items' data on every view (see Idempotency-adjacent design note under Data modelling, and the full reasoning in the architecture doc's Decision #37).

**General practical example:** a real e-commerce platform typically separates Orders, Inventory, Payments, and Users into independent services for the same reasons — different scaling needs, different teams, different failure domains.

**Interview points:**
- A service boundary is a *data-ownership* boundary first — "who's allowed to write this table" is the real question, not "which folder is this code in."
- The real cost is operational: more moving parts, network calls that can fail, and — accepted deliberately here — some duplicated boilerplate across services rather than one shared internal library.
- A monolith with clean internal module boundaries can defer almost all of that cost; microservices trade that simplicity for independent deployability and failure isolation.
- Service boundaries force real distributed-systems questions early (what happens if the other service is down, slow, or stale) that a monolith lets you postpone indefinitely.

---

## Service-to-service authentication / OAuth client credentials

**Simple theory:** When one backend service calls another on its own behalf (not for a logged-in person), it needs its own machine identity rather than a borrowed human session. OAuth2's client-credentials grant exists for exactly this: a service exchanges a `client_id`/`client_secret` for a short-lived access token.

**In our project:** Connectors never reuses anyone's login. It holds its own `client_id`/`client_secret`, exchanges them with Auth for a short-lived service token, and calls Items' ingest endpoint carrying that token. Items can tell a person from a service by the token's claims (a `sub` claim means a person; a `client_id` claim with no `sub` means a service) — and a service caller must say explicitly whose data this is, since the token itself carries no user identity.

**General practical example:** any backend job that pushes data into a third-party system (e.g. payroll pushing records into a benefits provider's API) typically authenticates this same way — a registered API client, never a human login.

**Interview points:**
- Never let a background process borrow a real user's session token — it blurs "who actually did this" and inherits that user's entire permission set unnecessarily.
- A service token should be distinguishable from a user token by its claims, and every endpoint accepting either must explicitly branch on which it received.
- This is close to SailPoint/IdentityIQ's own core domain — a connector authenticating to a target system under its own machine credential, not a borrowed one, to provision or sync data.
- Revocation looks different for a service credential than a user session: rotating a compromised client secret, not invalidating one specific token.

---

## OAuth2 and PKCE — 🟡 authorization built, data fetch pending

**Simple theory:** OAuth2's Authorization Code flow lets a user grant a third-party app limited access to their account on another service, without ever handing that app their password. PKCE (Proof Key for Code Exchange) adds a cryptographic proof that whoever completes the token exchange is the same party that started it.

**In our project:** the full Authorization Code + PKCE handshake with X (Twitter) is built and verified end to end (Decision #56) — a "Connect Twitter" button sends the user to a real X consent screen; a callback endpoint exchanges the resulting code for real access/refresh tokens and stores them. **Still pending:** actually calling X's API to fetch bookmarks with those tokens — deferred until API credits are purchased, since unlike authorizing, that step costs real money per read. Two things worth knowing that weren't obvious from theory alone until actually building this:
- The textbook framing ("PKCE is for public clients that can't hold a secret") isn't the whole story — **X requires PKCE on every app, including confidential, server-side ones** like this one, which already holds a real client secret. PKCE and "can this app hold a secret safely" turned out to be two separate questions, not one.
- The PKCE `code_verifier` needs somewhere to live *server-side* between the redirect to X and the callback minutes later, since the browser carries no session across that gap. Built as a small, short-lived database table (state → verifier), following the same pattern as this project's other opaque, DB-tracked tokens (refresh tokens, invite tokens) rather than inventing a new mechanism.

**General practical example:** "Sign in with Google" or "Connect your Spotify account" buttons — the requesting app never sees your actual Google or Spotify password.

**Interview points:**
- Know the difference: Authorization Code (server-side apps that can hold a secret) vs. Authorization Code + PKCE (originally for public clients that can't) — but don't assume every provider draws that line the same way; verify per-provider rather than assuming.
- PKCE stops an intercepted authorization code from being redeemed by an attacker, by requiring a matching secret only the original requester generated.
- Client credentials (previous entry) and Authorization Code/PKCE solve different problems — "a service acting as itself" versus "a user delegating limited access to a third party."
- A multi-step redirect flow (browser leaves your app, comes back later, to a *different* endpoint) always needs some server-side place to hold state across that gap — recognize this as the same shape as any "pending until confirmed" pattern (email verification links, payment redirects), not something OAuth-specific.
- It's fine, and more credible in an interview, to be precise about exactly which part is built (the handshake) versus pending (the actual data pull) — rather than a blanket "yes" or "no."

---

## Data modelling

**Simple theory:** Deciding what the real-world "nouns" of a system are (entities), what data belongs to each, and how they relate — settled before worrying about a specific database's columns and types.

**In our project:** entities were derived directly from user journeys (what actually happens, step by step) before any schema was drawn: User, Connection, Item, Board, Access Grant — each earning its own table because *something needs to read it again later*, independent of the moment it was first created.

**General practical example:** any new product feature starts here — "what are the nouns" (a customer, an order, a line item) before "what SQL do I write."

**Interview points:**
- A good litmus test for "does this need its own entity": does a background process need to read this again later without the original actor present? If yes, it's data. If it only matters in the instant it happens, it might just be logic.
- Get entities and relationships right before schema design (columns, types, indexes) — the two are genuinely separate steps.
- Entity boundaries often mirror service boundaries in a microservices system — "who owns this entity" is the same question as "which service owns this table."
- Denormalization (storing a copy of data instead of referencing it live) is a deliberate data-modeling trade-off to be able to name and defend, not an accident — see Board's item snapshot, next.

---

## PostgreSQL / service-owned data

**Simple theory:** A relational database enforces structure (types, constraints, foreign keys) and guarantees (uniqueness, referential integrity) at the data layer itself, not only in application code.

**In our project:** one Postgres instance, one schema per service, real foreign keys only *within* a service's own schema — a reference that crosses into another service's schema is a plain UUID column, validated by application code, never a real cross-schema FK. A unique constraint on `items (owner_user_id, source, external_id)` is what actually makes duplicate-safe ingestion possible (see Idempotency, below) — the database itself rejects a second insert of the same bookmark.

**General practical example:** most production systems still default to Postgres/MySQL for anything with real relationships and consistency requirements, reserving NoSQL stores for cases where their specific trade-offs (looser schema, different scaling model) genuinely pay for themselves.

**Interview points:**
- "Service-owned data" can be approximated with schema separation inside one database instance — a real, common middle ground before committing to fully separate physical databases.
- A unique constraint at the database level is a stronger guarantee than an application-level "check first, then insert" — it's race-free by construction; a genuinely concurrent duplicate request can't slip through.
- Real foreign keys should stop at a service boundary — a literal cross-service foreign key isn't possible in a true database-per-service split, so don't fake one just because it happens to share an instance.
- Postgres was chosen here for the real relational structure (boards, items, grants reference each other) — a deliberate fit, not a default habit.

---

## Idempotency

**Simple theory:** An operation is idempotent if doing it more than once has the same effect as doing it once — essential for anything that might be retried (network failures, timeouts, at-least-once delivery).

**In our project:** re-ingesting a bookmark that's already been ingested (same owner, source, and original ID) returns the existing item as a success — not an error, not a duplicate. A real sync naturally re-sends bookmarks it's already sent before, and that has to be a non-event, not a failure.

**General practical example:** payment APIs (e.g. Stripe) require an idempotency key on charge requests for exactly this reason — a retried request after a network blip must never double-charge someone.

**Interview points:**
- Idempotency is a property of the operation's *effect*, not of whether it's technically legal to call twice.
- The standard signal that you need it: any operation that might be retried automatically — client timeout-and-retry, at-least-once message delivery, a resumed sync.
- Achieved here via "insert and catch the constraint violation," not "check then insert" — the latter has a genuine race condition under concurrent duplicate requests.
- Idempotent isn't the same as side-effect-free — ingest still does real work the *first* time; only the repeat is a safe no-op.

---

## CORS (Cross-Origin Resource Sharing)

**Simple theory:** A browser-enforced security policy that blocks a webpage from *reading* a response from a different origin (different domain, port, or protocol) unless the server explicitly allows it via response headers. Enforced entirely client-side — the server can process the request just fine and still have its answer hidden from the page.

**In our project — a real bug, twice.** First: the web UI (`localhost:5173`) couldn't call Gateway (`localhost:8000`) at all until Gateway added an explicit CORS allowlist — the request reached Gateway fine, the browser was hiding the response. Second, in Firefox specifically: Chrome fully exempts an installed extension's own pages from CORS, but Firefox does not — it still sends a real preflight request that Gateway had to be taught to allow for extension origins too.

**General practical example:** any single-page app calling an API on a different subdomain or port hits this immediately in local development — one of the most common "works via curl, fails in the browser" bugs.

**Interview points:**
- CORS is purely a browser-side policy — curl, Postman, or a mobile app calling the same API is completely unaffected, which is exactly why an automated test suite using a plain HTTP client won't catch a missing CORS header.
- A cross-origin request with a non-"simple" method or header (like `Content-Type: application/json`) triggers an invisible preflight `OPTIONS` request before the real one is even sent.
- Don't assume a security exemption is identical across browsers without checking — it genuinely wasn't here.
- Never combine a wildcard allowed-origin with credentialed requests — browsers reject that combination outright; use an explicit allowlist (exact-match, or a narrowly-scoped pattern for a known class of origin like an installed extension).

---

## Database migrations

**Simple theory:** A versioned, incremental, reproducible way to evolve a database schema over time — with a clear history, and the ability to know exactly what's been applied where.

**In our project:** each service uses Alembic with its own independent migration history, scoped to its own schema. A real bug happened here: without scoping each service's version-tracking table to its own schema, two services' migration histories collided on the same shared tracking table — fixed by having each service's migration bootstrap create and use its own scoped version table.

**General practical example:** every production system with a real schema needs this — Django migrations, Rails' ActiveRecord migrations, Flyway, and Alembic all solve the same problem for different ecosystems.

**Interview points:**
- A migration tool's real job: track which schema changes have already been applied where, so the same migration never runs twice and every environment converges to the same schema.
- In a database-per-service (or schema-per-service) system, each service's migration history must be genuinely independent — sharing the tracking mechanism silently breaks that independence, as found here directly.
- A one-time init SQL script has no rollback story and can't safely evolve a table that already holds real data — migrations are what make schema change safe once data exists.
- Migrations running automatically at service startup is what makes "clone the repo, run one command" actually true — no manual per-environment step to remember or forget.

---

## Docker / containerization

**Simple theory:** Packaging an application with everything it needs to run (code, runtime, dependencies) into one portable unit that behaves identically regardless of the host machine.

**In our project:** every service has its own Dockerfile; `docker-compose.yml` brings up all five services plus Postgres together, in the correct dependency order, gated by real healthchecks (not just "the container started") — so a service that needs Auth's public key at startup doesn't crash-loop waiting for Auth to actually be ready.

**General practical example:** virtually every modern backend team ships this way now — a laptop, a CI runner, and a production host all run the identical container image.

**Interview points:**
- `depends_on` alone only waits for a container to *start*, not for the application inside it to be ready — a real healthcheck condition is what actually prevents startup-order bugs.
- Containerizing everything (rather than leaving some services manual) gives a genuinely reproducible "clone and run one command" experience — verified here with a full teardown-and-rebuild from an empty volume.
- Each service's own Dockerfile mirrors the same independent-deployability principle microservices are supposed to have.
- Containers solve "works on my machine," not architecture — they're orthogonal to service boundaries, data ownership, or auth design, not a substitute for getting those right.

---

## Basic reliability lessons — the bookmark-sync timeout incident

**Simple theory:** Timeouts, bounded concurrency, and graceful error handling are what keep a system usable when a dependency is slow or a request is unusually large. Reliability failures often first show up as a confusing symptom far from their actual root cause.

**In our project:** a real user's first sync of hundreds of real bookmarks failed with a cryptic client-side JSON-parsing error. The real chain: a fully sequential sync loop was slow enough to exceed Gateway's timeout → Gateway's *unhandled* timeout produced a non-JSON error page → the browser extension's code assumed every response was JSON and crashed trying to parse it. No automated test caught it, because no test used a realistically large batch.

**General practical example:** this is the shape of countless real production incidents — a slow downstream dependency causing a timeout, whose error-handling path was never actually exercised until real scale hit it.

**Interview points:**
- A confusing, seemingly-unrelated symptom (a JSON parse error) can be several layers removed from the real root cause (a slow sequential loop) — trace the whole chain, don't just patch the visible symptom.
- Bounded concurrency (not unlimited, not fully sequential) is a common, practical middle ground for batch operations against a downstream dependency.
- Every network call to another service needs an explicit timeout and explicit handling of what happens when it's exceeded — an unhandled timeout is a real production bug, not an edge case.
- Defensive parsing on the client side (read as text before assuming JSON) is cheap insurance against the *next* unanticipated error shape, not just the one just fixed.

---

## Topics to study separately later

Not yet reached by this project, and not worth forcing in artificially — study these directly rather than waiting for a forced project tie-in:

- Caching (e.g. Redis) and cache-invalidation strategy
- Message queues / async processing (Kafka, RabbitMQ, Redis Streams)
- Load balancing (L4 vs L7) — not reachable at this project's single-instance scale
- Sharding & consistent hashing — a personal single-user app will never need this
- NoSQL trade-offs (e.g. DynamoDB) — this project only uses Postgres, deliberately
- Blob storage & CDN — currently only favicon *URLs* are stored, not actual files
- Full service-mesh patterns (mTLS, SPIFFE/SPIRE) — this project approximates the same identity principle via OAuth2 client credentials, without the mesh infrastructure a much larger org would run
