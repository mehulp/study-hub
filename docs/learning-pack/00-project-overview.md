# Study Hub — Project Overview

*Part of the [learning pack](./). See [`01-system-architecture.md`](01-system-architecture.md) next.*

## What it is

Study Hub is a tool for curating and sharing interview-prep learning resources — save a
resource (title, URL, notes, tags), organize it into named Learning Plans, and share a
curated board with a study partner under real role-based access control. It's a full
five-service microservices system: a React frontend, an API Gateway, and four backend
services (Auth, Items, Board, Connectors), deployed for real on Railway and Cloudflare
Workers.

## The problem it solves

Studying for system-design interviews means collecting a lot of scattered material —
articles, videos, reference docs — with no good way to organize it by topic, track what's
actually been worked through, or share a curated set with someone else studying the same
material. Study Hub is that organizing layer: tag-based curation instead of folders, named
plans with per-item progress instead of a flat bookmark list, and real sharing instead of
copy-pasting a list of links into a chat.

## Main user journeys

1. **Save and organize** — add a resource with tags and notes; browse/filter the library by
   tag, search, or sort.
2. **Track progress** — group resources into a named Learning Plan, set per-item status
   (not started/in progress/completed) and a target date; a "Continue Learning" view on the
   library page surfaces what's in progress or due soon, across every plan.
3. **Share with a study partner** — select resources, create a board, invite someone by
   email. They get a real, RBAC-enforced Viewer role — see everything, change nothing.
4. **Receive and adopt** — the invited person opens the link, signs up or logs in, lands
   directly on the shared board, and can copy any item straight into their own library to
   build on it independently.

## Why I built it

Two goals at once: a genuinely useful personal tool, and a hands-on way to rebuild real
system-design fluency — service boundaries, authentication/authorization, RBAC, real
deployment — ahead of Senior EM/Director interviews. It's deliberately not a coding-skill
exercise. The point was being able to defend every architectural choice, not just ship
working code — which is why a full decision log (94 entries and counting) sits alongside
the code, capturing what was chosen, what the alternatives were, and why.

It also has real history: it started as a personal bookmark manager (`bookmarks-hub`), and
was forked once real use made clear that a study-resource tool was a more honest, more
interesting product for the same underlying engineering. That pivot — and the decision to
say so plainly rather than hide it — is itself part of the story (see Decision #59).

## Major technologies

- **Backend**: Python, FastAPI, SQLAlchemy, Alembic migrations, Postgres (one instance,
  schema-per-service)
- **Auth**: RS256 JWTs (asymmetric — Auth signs with a private key, every other service
  verifies with the public key alone), Argon2id password hashing, DB-tracked refresh tokens
  with rotation + reuse detection, OAuth2 client-credentials for service-to-service identity
- **Frontend**: React, TypeScript, React Router, Vite — no state-management library beyond
  React's own Context API
- **Deployment**: Docker Compose locally; Railway (backend services + Postgres) and
  Cloudflare Workers (static frontend) in production

## Major architectural ideas

- **Real microservices, not a monolith with folders** — five independently deployable
  services behind a Gateway, chosen specifically to get hands-on with service boundaries,
  not because the app's actual scale needs them.
- **Zero Trust between services** — the Gateway validates a request's JWT once, but every
  backend service independently re-verifies it too, rather than trusting that a request
  reaching it must already be legitimate just because of where it came from.
- **Schema-per-service, one Postgres instance** — each service owns its own schema with no
  cross-schema foreign keys (soft references only, validated in application code), the
  practical middle ground between a shared database and fully separate database instances.
- **Deliberate denormalization, stated as a trade-off, not an accident** — a shared board
  stores its own snapshot of an item's display fields at add-time rather than calling Items
  live on every view, because Items only ever answers "what are *your* items" — which
  breaks the moment someone the board was shared with tries to view it.

## What makes it more than a CRUD app

The obvious version of this product is a single table with a create/read/update/delete
form. What actually makes it interesting to talk about in an interview isn't the CRUD parts
— it's everything CRUD doesn't cover: how five independent services agree on who a user is
without a shared session, what happens when a shared resource's data goes stale, how a
receiver with zero login history lands directly on the right board with no manual "accept"
step, and what it costs (in code, in trade-offs) to make service boundaries real rather than
decorative.

## The 60–90 second answer

> "Study Hub is a resource-curation tool I built to relearn system design hands-on before
> Senior EM interviews — you save study resources with tags, organize them into learning
> plans with progress tracking, and share a curated board with a study partner under real
> role-based access control. It's five separate microservices — a gateway, auth, items,
> board, and a connectors service — each with its own Postgres schema, talking to each
> other over real network calls, not just function calls in one codebase. The interesting
> parts aren't the CRUD — it's things like RS256 JWTs where only the auth service ever
> holds the private key, every service independently re-verifying tokens instead of
> trusting the gateway's word for it, and a deliberate trade-off where a shared board
> snapshots an item's data at share-time instead of calling the items service live on every
> view. It's fully deployed — Railway for the backend, Cloudflare Workers for the frontend
> — and I kept a full decision log the whole way, about 90 real entries, specifically so I
> could defend every choice rather than just have something that works."
