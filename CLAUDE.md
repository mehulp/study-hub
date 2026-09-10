# CLAUDE.md — mp-project-study-hub

## What this project is

"Mehul's Study Hub" — a tool to curate and share system-design/interview-prep learning
resources with study partners. It's a fork of `bookmarks-hub` (a personal bookmark manager,
`git clone`d with full history preserved, no remote link back — now fully independent).
Same underlying architecture (five services, RS256 JWTs, OAuth2, RBAC, schema-per-service
Postgres, a browser extension, a React/TypeScript web UI); different, more portfolio-honest
product framing. `bookmarks-hub` itself is untouched and continues as a separate, ongoing
personal project — do not confuse the two or edit one thinking it's the other.

The fork itself is not hidden: it's documented plainly in
`docs/study-hub-architecture.md` (Decision #59) as a good signal (real experience
justified the pivot), not something to paper over.

## Primary source of truth

**Read `docs/study-hub-architecture.md` first, every session.** It's the full
Decision Log (Problem/Options/Decision/Why/Trade-off reasoning, numbered decisions,
currently through #61) plus the architecture, data model, and service boundaries. Treat it
as authoritative over assumptions from memory or from this file — but also verify it's
still accurate before relying on it for fast-changing facts (see below).

## Working style (explicit user preference)

- **Step by step, one decision at a time.** Explain what's chosen, the alternatives, and
  why, before moving on. No large chunks of code without an understanding checkpoint first.
- **Log every real decision** into the Decision Log in
  `docs/study-hub-architecture.md` — terse rows in the `## Decision Log` table for
  every decision; the fuller Problem/Options/Decision/Why/Trade-off prose format is
  reserved for the `## Architectural Learnings` section, for the strongest/most teachable
  lessons only (not every decision gets one). **Never delete superseded decisions — mark
  them superseded**, in place, with a note pointing to what replaced them.
- **Only commit when explicitly asked.** Don't commit proactively after finishing a task.
- **After scaffolding new code, give a mechanics walkthrough** — how it actually works,
  file by file — not just the decision rationale. This is a learning project; the point is
  understanding, not just working code.
- **Verify external/fast-changing facts** (hosting pricing, API behavior, etc.) rather than
  trusting old notes or assumptions. The architecture doc's Render-hosting note is known to
  be stale — recheck real hosting options/pricing before Phase 5 (deployment), don't just
  reuse the old note.
- **Be honest about gaps** rather than papering over them.

## Project-specific facts worth remembering

- **Docker ports are deliberately shared** between mp-project-study-hub and
  `bookmarks-hub` (simpler, only one runs at a time, rather than each getting its own).
  `start-dev.sh` in both projects already checks for the sibling's containers and refuses
  to start if they're up — this is built and tested, don't redo it or "fix" it.
- **Doc cleanup** (removing/rewording bookmark-specific language in the cloned docs) should
  happen incrementally, alongside Phases 0–2, as each area is actually touched — not as a
  separate upfront pass. Keep the fork/pivot note; just don't let bookmark-specific
  phrasing linger scattered through docs once it's been superseded by something in the
  Decision Log.

## Phased plan (current status)

- **Phase 0 — ✅ Done.** Resource-input decision: manual entry via the web UI is the
  primary path; browser-extension-style capture is deferred to a real later phase, not
  dropped (Decision #60). Twitter/X repurposed as generic link-paste, not live API
  fetching; the existing OAuth2+PKCE code is kept in place, unused (Decision #61).
- **Phase 1 — ✅ Done (Decisions #62–64, backend only).** Study resources get free-text,
  multi-valued tags via a new `items.item_tags` join table (not a `category` column,
  `folder_path` stays untouched/dormant) — Decision #62. Manual items use
  `source="manual"`, `external_id` = the pasted URL itself, and `"twitter"` is retired as a
  source value — Decision #63. Items gained real `PATCH`/`DELETE` endpoints (owner-scoped)
  plus a nullable `notes` column — Decision #64, which also flags that this invalidates
  part of Decision #37's "items never change after saving" assumption behind Board's
  denormalized snapshot (unresolved, revisit in Phase 2+). Built and tested: migration
  `0002` (`services/items/alembic/versions/`), `ItemTag` model + `Item.tags`/`notes`
  (`services/items/app/models.py`), widened `Source` + `ItemUpdateRequest`
  (`services/items/app/schemas.py`), `PATCH`/`DELETE` endpoints + tag-normalization helper
  (`services/items/app/main.py`) — 32 passing tests in `services/items/tests/test_items.py`,
  plus a live smoke test through the real Docker stack. **Not yet built:** any of this
  surfaced in the web UI — that's Phase 2.
- **Phase 2.** Web UI rework: rebrand to "Mehul's Study Hub," rework the dashboard to
  browse by category instead of Twitter/Browser source.
- **Phase 3.** Secrets hygiene: `OAUTH_CLIENT_SECRET` and `POSTGRES_PASSWORD` are currently
  hardcoded in `docker-compose.yml` — move to `.env`, rotate the OAuth secret value.
  (`TWITTER_CLIENT_SECRET` is no longer in scope here per Decision #61.)
- **Phase 4.** Seed a real demo account with genuinely good curated resources + a shared
  board.
- **Phase 5.** Deploy for real — verify current hosting options/pricing first, don't trust
  the architecture doc's old Render note.
- **Phase 6 — deliberately last, even after deployment.** Push to GitHub, write a README
  that leads with the architecture/Decision Log story, not "it's a bookmark manager."
