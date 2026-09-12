# Study Hub — System Design Interview Questions

*Part of the [learning pack](./). Previous: [08-interview-project-walkthrough.md](08-interview-project-walkthrough.md). Next: [10-one-page-cheatsheet.md](10-one-page-cheatsheet.md).*

Questions organized by category, answered specifically against this system — not generic
system-design theory. For SailPoint/IAM-specific framing of the auth/RBAC material, see
`docs/sailpoint-prep-coverage-map.md`.

## Architecture

**Why microservices for a personal-scale app?**
Explicitly to build hands-on fluency with real service boundaries, not because the traffic
needs it — stated directly, not hidden behind a technical-sounding justification. A modular
monolith would be objectively better-suited to the actual scale.

**Why does Connectors exist if it's not live?**
It's real, demonstrated engineering — a working OAuth2+PKCE handshake against Twitter's
real servers, a browser-extension push-token flow — kept as a distinct service because
acting on a user's behalf against an external, untrusted system is a genuinely different
trust boundary than anything else in the system, even though the live product never
exercises the fetch/sync path.

**Why does Learning Plans live inside Items instead of being its own service?**
Because none of the criteria that justified Board becoming its own service apply to it —
no sharing, no RBAC beyond plain ownership, no independent scaling story. Drawing a service
boundary around a feature just because it's a named feature would have been the wrong
criterion.

## APIs

**Why does Gateway forward requests instead of each service being reached directly?**
One consistent entry point for CORS, coarse auth, and routing — a client only ever needs to
know one address, and every route's basic "is this a logged-in user" check happens in
exactly one place instead of five.

**Why does adding an item to a board call Items synchronously instead of trusting the
client's own data?**
The client could lie about an item's title/tags. Board asks Items directly, using the
caller's own token, so Items applies its normal ownership check — confirming the item is
really the caller's own — before Board ever stores anything.

**Why is a duplicate resource save (same URL) a 200, not a 409 or a silent overwrite?**
Re-ingesting something you already have is routine, expected behavior (a re-sync, a
"save to my resources" on something already saved) — treating it as an error would make
normal use look broken. It's returned as an idempotent success with the existing row, not
silently duplicated and not silently overwritten either.

## Database

**Why one Postgres instance instead of one database per service?**
The textbook microservices pattern (fully separate database instances) is meaningfully
heavier to operate locally than this project needs. Schema-per-service is the middle
ground: the discipline that actually matters (no service reaches into another's tables) is
kept, without multiplying containers.

**Why no foreign keys across schemas?**
A cross-schema FK would quietly recreate the coupling schema separation exists to prevent.
Cross-schema references are plain UUID columns, validated once by application code at
write time — a real, named trade-off (see the next question).

**What actually breaks because of that choice?**
Referential integrity across a service boundary is only as strong as the one write-time
validation call — nothing stops a referenced row from later being deleted or changed
without the referencing service knowing. Concretely: Board's item snapshot can go stale
relative to Items' live data, and that's an accepted, explicitly-named cost, not an
oversight.

**Why does `PlanItem.item_id` get a real foreign key but `BoardItem.item_id` doesn't?**
Because Plans and Items share a schema (real FK, DB-enforced) while Board is a genuinely
separate service with its own schema (soft reference, code-enforced). Same underlying
question — "does this item exist" — two different enforcement mechanisms, purely as a
function of which schema each table lives in.

## Authentication / Security

**Why RS256 instead of a shared-secret JWT?**
Asymmetric signing means only Auth can mint a token; every verifier holds only the public
key, so compromising a downstream service can't be used to forge tokens system-wide — see
[`05-authentication-authorization-rbac.md`](05-authentication-authorization-rbac.md) for
the full answer.

**How do refresh tokens work, exactly?**
Opaque random value, hashed before storage, looked up in Postgres on every use (unlike the
access token, which is verified by signature alone, no DB hit). Every refresh **rotates**
it — the old row is marked revoked and replaced, a new one issued — and presenting an
already-rotated token again triggers reuse detection, revoking every active token for that
user.

**How is RBAC enforced, concretely?**
Two layers: Gateway asks the coarse question (valid logged-in user?) on every request;
Board independently asks the fine-grained question (owner, accepted viewer, or nobody, for
*this specific* board) on every board-mutating action, checked fresh each time rather than
cached from a prior check.

**What would you have done differently on the invite-link security model?**
Named directly: the invite link isn't checked against the invited email at accept time —
whoever holds the link and is logged into any account gets access, a deliberate "anyone
with the link" trade-off (Decision #39), not an oversight. At real product scale I'd revisit
requiring the accepting account's email to match, especially once real email delivery
exists to make that enforceable without breaking the flow.

## Scaling

**How would this scale to 1M users?**
Client-side search/filtering is the first thing that breaks — it assumes a user's full item
list fits comfortably in one fetch and one render pass; that stops being true well before
1M users, more like low-thousands of items *per user*. Board's synchronous item-snapshot
call to Items on every add would also need real backpressure/retry handling under load it's
never had to survive. Refresh-token verification hitting Postgres on every single refresh
becomes a real hot path worth caching (see below).

**What's the actual bottleneck today, if any?**
None, in practice — real traffic is one to a handful of users. The architecture was
deliberately built heavier than current load needs, specifically to have real answers to
scaling questions rather than to solve a scaling problem that doesn't exist yet.

## Caching

**Where would Redis make sense?**
Two concrete candidates, not a generic "add Redis" answer: refresh-token revocation checks
(currently a Postgres round-trip on every single `/refresh` call — a natural sub-millisecond
cache), and Auth's JWKS response if the number of verifying services or request volume ever
grew enough to matter (currently fetched once per service at startup and cached in-process,
so there's no real pressure yet).

**Why isn't Redis in the system today?**
Nothing in the actual roadmap ever produced a workload it solves — every progress/summary
view is either client-side-derived or a cheap query over a small personal dataset. Standing
rule: new infrastructure gets adopted when a real feature creates an actual need for it,
never because it's a common interview topic.

## Failure handling

**What happens if Auth is down?**
Every other service loses the ability to verify *new* logins/refreshes, but already-cached
public keys mean in-flight requests with still-valid access tokens keep working for up to
15 minutes — the access token's short lifetime is exactly what bounds that blast radius.

**What happens if Items is down while adding something to a board?**
Board's add-item call to Items fails, and that's surfaced as a real `503` to the client —
not swallowed, not silently retried into a bad state. Verified directly as a real regression
test (`test_add_item_returns_503_when_items_service_fails`), not just a theoretical case.

**What happens if email delivery fails?**
There is no email delivery to fail — invite links are shown in the UI for manual copy/paste
by design (Decision #38), so this entire failure mode doesn't exist in the current system.
Worth naming as a real question for the version of this that *did* have real email.

## Deployment

**Why Railway + Cloudflare Workers specifically?**
Concretely ruled out AWS App Runner (no longer accepting new customers), Fly.io (no free
tier for new accounts), Render (free tier can't cover 5 always-on services), and
DigitalOcean (~$25/mo minimum) — see [`07-key-design-decisions.md`](07-key-design-decisions.md#13-deployment-platform-railway--cloudflare-workers-decisions-87–91).

**What was the hardest part of actually deploying it?**
Two real, live-debugged issues, not hypothetical ones: Railway's private-networking
hostnames aren't the bare Docker Compose service names (`http://auth:8001` doesn't
resolve there), and a raw multi-line PEM pasted into a single-line dashboard input field
silently loses its newlines, breaking key parsing — fixed by switching to base64-encoded
key material instead.

## Observability

**What's the current gap, honestly?**
No centralized logging or metrics beyond each platform's own basic dashboard/console logs.
A real, named gap for a system this size in production — the next thing worth adding if
this moved from personal to real-team use would be structured logging with a request ID
threaded through Gateway → backend service, so one failed request could be traced across
service boundaries.

## Trade-offs

**What's the single trade-off you'd most want to talk about?**
Board's item snapshot — see decisions #8 and #14/#15 in
[`07-key-design-decisions.md`](07-key-design-decisions.md). It's a real, load-bearing
architectural choice with a named cost (staleness), a concrete instance where that cost
actually surfaced as a bug (tag-less saved copies), and a separate, deliberate decision
*not* to fully fix the underlying staleness because the fix wouldn't have solved the real
problem. That's three layers of real engineering judgment in one trade-off, not just a
single decision.
