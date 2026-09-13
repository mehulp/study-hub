# Known Limitations

A live-maintained list of real gaps found after the functional scope froze
(`study-hub-architecture.md`'s "Near-Term Direction" section, 2026-09-12). Separate from
that doc's own historical backlog, which is explicitly frozen and not meant to be read as
active guidance — this one is meant to be updated: never delete an entry, mark it resolved
in place with the decision number that closed it, same discipline as the Decision Log.

## Open

### Only one recipient can be invited at a time

**What happens today:** both invite flows — `ShareDialog.tsx` (create a new board and
share) and `InviteToBoardDialog.tsx` (add someone to an existing board) — take exactly one
email address per submission. `POST /{board_id}/invite`'s request body
(`InviteRequest.invited_email`) is a single `EmailStr`, not a list. Sharing with 3 people
today means 3 separate invite actions on the same board (which the app does support,
Decision #76) — not a single "invite several people at once" flow.

**What a real fix would need:** `invited_emails: list[EmailStr]` on the backend, a
batch-create over `AccessGrant` rows (each still gets its own token — an invite link is
inherently one-token-per-recipient, so this is "one submit, several grants created," not a
single shared link), and a multi-email input on the frontend (chips or comma-separated),
with each address's success/failure surfaced individually since one could already be
invited while another isn't.

**Status:** confirmed gap, deliberately not built — scope is frozen.

### No real email is sent for an invite — it's a link you copy and send yourself

**What happens today:** creating an invite (either flow) generates a real, working invite
link and shows it in the UI once — nothing gets emailed to the recipient automatically. The
owner has to copy it and send it themselves, by whatever means (Decision #38 — original
call: no transactional email provider, kept intentionally simple).

**Already designed, not built:** a full proposal for real delivery via Resend was written
in detail later — including revisiting Decision #39 (the invite link isn't checked against
the invited email at accept time; "anyone with the link" gets in, first-come-claimed) to go
with it, since real email delivery makes that trade-off worth re-examining. Explicitly
declined at the time: the existing signup-from-invite return-path flow already supports
manual sharing with zero new code, and the owner was fine sending links manually. Not a gap
found by accident — a real feature, scoped, and consciously not built.

**What a real fix would need:** an email provider integration (Resend was the one actually
evaluated — real API/pricing checked, not assumed), a transactional template, delivery
failure handling (what happens if sending fails — does invite creation still succeed?),
and very likely revisiting Decision #39 alongside it, per the reasoning above.

**Status:** confirmed gap, deliberately not built — scope is frozen.

### No `AsyncClient` reuse for outbound HTTP calls

**What happens today:** every outbound `httpx` call (Gateway's proxy — on *every* request —
plus Board's `items_client.py`/`auth_client.py` and Connectors' `items_client.py`)
instantiates a fresh `async with httpx.AsyncClient() as client:` per call, rather than one
long-lived client reused across requests. httpx's own guidance recommends the latter for
connection pooling/keep-alive.

**Why not fixed now:** found during the pre-publication audit; real, but invisible at this
app's actual traffic, and Gateway's proxy is the one place *every* request flows through —
changing that pattern right before a public release carries more regression risk than the
current benefit justifies. A pool-exhaustion or connection-leak bug introduced here would
be worse than the inefficiency it replaces.

**Status:** confirmed, deliberately deferred — good candidate for its own isolated change,
not a pre-release batch.

### `tsconfig.app.json` doesn't enable `strict` mode

**What happens today:** only individual flags are set (`noUnusedLocals`,
`noUnusedParameters`, `noFallthroughCasesInSwitch`) — no `strict: true`, so implicit `any`
and missing null-checks aren't compile errors. A grep for actual `any`/`as any` usage across
`web/src/` found zero — nobody's relied on the laxity so far, this is about the safety net,
not an active problem.

**Why not fixed now:** turning it on could surface an unknown number of new null-safety
errors across 51 TS/TSX files, each needing individual judgment, not a mechanical fix.
Real, deliberate risk-benefit call: doing this properly deserves its own isolated pass with
room to actually look at each surfaced error, not a rushed pre-release batch.

**Status:** confirmed, deliberately deferred.

### A narrow race window in invite acceptance

**What happens today:** `accept_invite` does a read-then-write (`if grant.user_id is None:
...`) without a row lock. Two genuinely concurrent accepts of the same still-pending invite
token could theoretically both pass the check before either commits.

**Why not fixed now:** real but negligible at this app's actual concurrency (personal-scale
traffic, near-zero chance of two people racing to accept the exact same invite in the same
instant). Fixing DB locking for this would be over-engineering relative to the actual risk.

**Status:** confirmed, deliberately left as a documented trade-off, not a bug to chase.

## Security notes

### A rotated OAuth client secret exists in git history

`git log -p` on `docker-compose.yml` shows a real `OAUTH_CLIENT_SECRET` value hardcoded in
an early commit, before Decision #66 moved secrets to a gitignored `.env`. Found during the
pre-publication audit and flagged explicitly per the audit's own instruction to surface any
secret that ever existed in a tracked file, even if since removed.

**Current risk: none.** Per Decision #66, this exact secret was rotated (regenerated via
`create_oauth_client.py`) — the value in history is dead and has never matched the live
secret since. Deliberately **not** scrubbed from git history: that requires a destructive
history rewrite (`git filter-repo` + force-push), and rewriting history for a credential
that no longer works trades a real, if small, disruption for a symbolic cleanup. Documented
here instead, consistent with this project's own "honest about gaps" approach.

## Resolved

### Stat cards weren't clickable, even the ones with a real destination

**What was wrong:** the Library page's "Your Boards" and "Shared With You" stat cards
showed a real, non-zero count with no way to click through to `/boards` — a number that
implies something exists with no path to go see it. This was actually a deliberate
decision at the time (#81: "kept non-clickable...for consistency across the row"), not an
oversight — revisited once it became clear two of the five cards *do* have a real nav
target and three don't, so uniform non-clickability was optimizing for the wrong thing.

**Resolved by:** Decision #95 — `StatCard` gained an optional `to` prop (renders as a
`react-router-dom` `Link` only when passed), wired to `/boards` on just the two
board-related cards.

### Gateway forwarded raw upstream exception text to the client

**What was wrong:** a failed upstream call's `except httpx.HTTPError as exc` handler put
the raw exception string into the `502` response's `detail` field — potentially including
internal connection details (hostnames, ports) visible to an external caller.

**Resolved by:** the exception is now logged server-side (`logger.error(...)`); the client
gets a generic `"Upstream service error"` message. 17 Gateway tests pass unchanged.

### All 5 containers ran as root

**What was wrong:** no `USER` directive in any of the 5 Dockerfiles.

**Resolved by:** each Dockerfile now creates a non-root `appuser`, `chown -R`s `/app` after
`COPY . .` (so Auth's `entrypoint.sh` can still write JWT key files at runtime on a fresh
deploy, Decision #87), and switches to it before `EXPOSE`/`CMD`. Verified live: full stack
rebuilt, all 6 containers healthy, `docker compose exec <svc> whoami` confirms `appuser` on
all 5, and a real signup→login round-trip through Gateway still returns `200`.

### Python dependencies were unpinned

**What was wrong:** every `requirements.txt` (all 5 services) listed bare package names —
no version pins, no lockfile. `pip-audit` found no currently-known vulnerabilities in what
was installed, so this was a reproducibility gap, not an active one: a future clone could
silently pull a different, possibly-breaking version.

**Resolved by:** every `requirements.txt` now pins exact versions (direct + transitive),
taken from each service's already-tested, already-passing dev environment — not upgraded,
just locked to what was already proven working.
