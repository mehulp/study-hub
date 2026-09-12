# Study Hub — Interview Project Walkthrough

*Part of the [learning pack](./). Previous: [07-key-design-decisions.md](07-key-design-decisions.md). Next: [09-system-design-interview-questions.md](09-system-design-interview-questions.md).*

Four lengths of the same explanation, for whatever amount of airtime the moment actually
gives.

## 30-second version

> "Study Hub is a resource-curation and sharing tool I built as five real microservices —
> gateway, auth, items, board, and connectors — deployed on Railway and Cloudflare. I built
> it to relearn system design hands-on: real service boundaries, RS256 JWT auth with
> independent verification at every layer, and RBAC-based sharing, not just CRUD."

## 90-second version

> "Study Hub lets you save study resources with tags, organize them into learning plans
> with progress tracking, and share a curated board with a study partner under real
> access control. I built it as five separate microservices — a gateway, auth, items,
> board, and connectors — each with its own Postgres schema, talking over real HTTP, not
> function calls in one codebase.
>
> The parts I can actually defend in depth: JWTs are RS256, so only the auth service ever
> holds the private key — everything else verifies with a public key alone, and every
> service re-verifies independently rather than trusting the gateway's word for it, which
> is Zero Trust in practice, not just a buzzword. Sharing is real RBAC — an owner and a
> viewer, enforced per-request, not cached. And there's a deliberate trade-off I can talk
> through: a shared board snapshots an item's data at share-time instead of calling the
> items service live on every view, because items only ever answers 'what's mine' — which
> breaks the moment someone else tries to view a shared item.
>
> It's fully deployed — Railway for the backend, Cloudflare Workers for the frontend — and
> I kept a full decision log the whole way specifically so I could explain *why*, not just
> show that it works."

## 5-minute version

> "Study Hub started as a personal bookmark manager and I forked it once I realized a
> study-resource curation tool was a more honest, more interesting product for the same
> underlying architecture — I keep that history visible rather than hiding the pivot.
>
> The core idea: five independently deployable services behind a gateway — auth owns
> identity, items owns the resource catalog and learning plans, board owns sharing and
> access control, and connectors is a real but currently dormant integration surface
> (Twitter OAuth, a browser extension). Each service owns its own Postgres schema, with a
> hard rule against cross-schema foreign keys — soft references, validated once in
> application code, not enforced by the database.
>
> Authentication is RS256 JWTs — asymmetric, so only auth can mint a token and everyone
> else can only verify one. The gateway checks a token's signature and expiry before
> forwarding anything, but every backend service independently re-verifies the same token
> itself rather than trusting that gateway already checked it. That's a real, working
> instance of Zero Trust, not just a term I can define.
>
> Authorization splits the same way: gateway only ever asks 'is this a valid logged-in
> user,' a coarse check. Board asks the fine-grained question — is this specific user the
> owner or an accepted viewer of this specific board — because board is the only service
> that actually has that data.
>
> The trade-off I'm proudest of being able to defend: when someone views a shared board, it
> doesn't call the items service live. It stores its own snapshot of each item's display
> fields, copied once when the item is added. I can explain exactly why — items only
> answers 'what's mine,' which is right for the owner but wrong the moment a viewer who
> doesn't own the item tries to look at it — and exactly what it costs: if the source item
> changes later, the board's copy doesn't know. I found and fixed a real instance of that
> cost recently — a 'save this shared item to my own library' feature I added produced
> tag-less copies, because tags didn't exist yet when that snapshot was originally
> designed. The fix was widening the snapshot, not the bigger, wrong idea I considered
> first — making tags a global, cross-user concept.
>
> It's deployed for real — Railway for the backend, five services plus Postgres on private
> networking, one public domain; Cloudflare Workers for the frontend. And every real
> decision along the way — not just the big architectural ones, but things like why I
> didn't build a fix for the staleness gap once I realized it wouldn't actually solve the
> underlying problem — is written down in a decision log, close to a hundred entries now,
> specifically so I can defend any of it, not just point at working code."

## Deep-dive version — structure to navigate by

For a genuinely open-ended "walk me through it" conversation, this is the order that
naturally builds on itself — each section is its own doc in this pack if the conversation
goes deep on one:

1. **Problem** → why this exists, who it's for → [`00-project-overview.md`](00-project-overview.md)
2. **Product** → the four real user journeys (save, plan, share, receive) → [`00-project-overview.md`](00-project-overview.md)
3. **Architecture** → five services, why each boundary is where it is → [`01-system-architecture.md`](01-system-architecture.md), [`02-service-boundaries.md`](02-service-boundaries.md)
4. **Data model** → soft refs vs. real FKs, the one deliberate denormalization → [`03-data-model-and-erd.md`](03-data-model-and-erd.md)
5. **Authentication** → RS256, access/refresh tokens, rotation + reuse detection → [`05-authentication-authorization-rbac.md`](05-authentication-authorization-rbac.md)
6. **RBAC/sharing** → Gateway vs. Board's authorization split, Access Grants, invite tokens → [`05-authentication-authorization-rbac.md`](05-authentication-authorization-rbac.md)
7. **Deployment** → Railway + Cloudflare, what actually moving code to production looked like → [`06-deployment-and-runtime.md`](06-deployment-and-runtime.md)
8. **Important trade-offs** → the 15 decisions worth defending cold → [`07-key-design-decisions.md`](07-key-design-decisions.md)
9. **What I'd do differently at scale** → below

## What I would do differently at scale

Said plainly, not defensively — these are real limits of choices that were right at this
project's actual scale, not universal best practices:

- **Board's snapshot staleness would need a real fix.** At personal scale, a board's item
  data going stale after an edit is a non-issue nobody's hit. At real multi-tenant scale
  with active editing, I'd need either a service-to-service read path with a proper trust
  model (Board authenticating as itself, not borrowing a user's token) or an event-driven
  invalidation instead of relying on "nothing changes after creation" mostly holding true.
- **Client-side search stops working past a certain dataset size.** It's the right call at
  tens-to-hundreds of items per user; at real scale it becomes Postgres full-text search at
  minimum, and a proper search service if cross-item relevance ranking ever matters.
- **No caching layer anywhere.** Deliberately — nothing in this system's real workload
  produces cache pressure. At real traffic, Auth's JWKS endpoint and Items' hot-path reads
  are the obvious first candidates.
- **Refresh tokens are checked against Postgres on every use.** Fine at this scale; at real
  scale that's a natural Redis use case — sub-millisecond revocation checks without a
  full database round-trip on every single refresh.
- **Five services for what's still a small team's worth of traffic is real overhead.**
  I'd keep the boundaries (they're drawn on real ownership/trust lines, not arbitrarily)
  but would expect a real team to feel the operational cost of five independently deployed
  things sooner than I did building this alone.
