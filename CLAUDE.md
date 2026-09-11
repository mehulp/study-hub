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
- **Phase 2 — ✅ Done (core flow verified live by the user).** Rebranded to "Mehul's Study
  Hub" (header, page title). Twitter's UI removed entirely — `TwitterTiles.tsx` and
  `api/twitter.ts` deleted as genuinely dead code now that `source="twitter"` can never
  exist (Decision #63); the backend OAuth code stays, per Decision #61. `BrowserBookmarks`/
  `FolderTree` left untouched — still dormant, not dropped (Decision #60). New
  `StudyResources.tsx`: flat resource list with tag-chip filtering (not fixed sections —
  tags are multi-valued, Decision #62) plus `ResourceFormDialog.tsx`, one dialog for both
  create and edit (mirrors Decision #64's PATCH). Wired into `DashboardPage.tsx` with
  local-state updates on save/delete (no full re-fetch). Verified: TypeScript compiles
  clean, `oxlint` clean, full create/list/PATCH/DELETE contract confirmed live through
  Gateway, and the user confirmed the actual rendered UI (empty states, create flow, tag
  chip, notes, Edit/Delete buttons) in their own browser — this session's sandbox had no
  usable headless-browser environment (no system Chromium libs, no passwordless sudo), so
  that real-browser check came from the user, not from an automated screenshot here.
  Follow-up naming-consistency pass (user-requested, after seeing it work): renamed
  "Bookmarks Hub" branding and the `bookmarks_hub` identifier everywhere it meant *this*
  project — `web/package.json`'s `name` (now `study-hub-web`), the browser extension's
  manifest/HTML titles, `web/src/api/client.ts`'s localStorage keys and the
  `study_hub:logged_out` event (was `bookmarks_hub:...`), `check-dev-env.sh`,
  `sailpoint-prep-coverage-map.md`'s title, and — the bigger one — the Postgres
  user/database itself (`bookmarks_hub` → `study_hub` in `docker-compose.yml`, every
  service's test `conftest.py`, `run-tests.sh`, and `.env`/`.env.example` files), which
  required recreating the Postgres container + volume (old dev data wiped, by the user's
  own choice — see the Decision Log entry logged for this). Also fixed a real pre-existing
  bug found along the way: `daily-startup.md` still pointed at
  `/home/mehul/projects/bookmarks-hub` and `bookmarks-hub-postgres-1` — wrong for this
  repo's own copy of the doc, now corrected. Left alone, deliberately: every mention of
  `bookmarks-hub` that actually refers to the real sibling project (in `CLAUDE.md`,
  `start-dev.sh`, the fork note, Decision #59) — those are correct as-is. Decisions #1–58
  stayed untouched (historical, never edited). The `## Problem Scope` section's original
  "personal bookmarks hub" framing (browser-first, Twitter-second, organized by source) was
  a separate, genuine content rewrite — not just a naming fix — done as a follow-up once
  asked: it now describes the actual current product (manual entry + tag-based curation as
  primary, browser bookmarks dormant/deferred, Twitter fetching retired in favor of
  link-paste) instead of the pre-fork one.
  **Still open, low-stakes:** the favicon is unbranded (default Vite icon, never said
  "Bookmarks Hub" to begin with, so not actually part of this cleanup).
- **Phase 3 — ✅ Done (Decision #66).** `OAUTH_CLIENT_SECRET` and `POSTGRES_PASSWORD` moved
  out of `docker-compose.yml` into a root `.env` (gitignored, joining `TWITTER_CLIENT_SECRET`'s
  existing pattern) plus a tracked root `.env.example`. `OAUTH_CLIENT_SECRET` genuinely
  rotated (regenerated via `services/auth/create_oauth_client.py`) — convenient timing,
  since the `oauth_clients` table was empty after Decision #65's volume recreation, so
  Connectors' auth to Items was actually broken until this fix, not just theoretically due
  for rotation. `POSTGRES_PASSWORD` only relocated, value unchanged (not asked for, low
  stakes). Decision #57 marked superseded — its "OAUTH_CLIENT_SECRET can stay hardcoded"
  reasoning assumed a private local-only repo, which stops being true once Phase 6's GitHub
  push happens. Verified live: all six Docker services healthy, rotated secret confirmed
  against Auth's real `/oauth/token`, `docker exec printenv` confirmed containers actually
  received the substituted values.
- **Phase 4 — ✅ Done (Decision #67).** `mehulpatankar_owner@gmail.com` has 70 real
  system-design study resources (ByteByteGo/Hello Interview/YouTube, curated from a
  personal interview-prep checklist), a "System Design Fundamentals" board (48 items)
  shared with `mehulpatankar_receiver@gmail.com` and already accepted. Reproducible via
  `scripts/seed_demo_data.py` + `scripts/system_design_resources.csv` (curated, no
  personal progress-tracking columns — the source `.xlsx` stays local, gitignored).
  Credentials were shown once when the script ran; if lost, re-run the script (new random
  passwords each time) or reset via Auth directly.
- **Board-visibility backlog item — ✅ Done (Decision #68).** `GET /board/mine` (owner:
  boards owned, item counts, per-grant status) and `GET /board/shared-with-me` (recipient:
  boards with an accepted grant), registered before `GET /{board_id}` in `main.py` — order
  matters, see Decision #68. Web UI: `MyBoards.tsx`/`SharedWithMe.tsx` on the dashboard,
  with the share flow refreshing "Boards I've Shared" immediately on a new share. 37 Board
  tests pass (some pre-existing intermittent subprocess-startup flakiness, same category
  seen in Auth/Items earlier — isolated re-runs and full clean re-runs both confirm it's
  not caused by this change). Verified live against the real Phase 4 demo data.
- **Complete local testing pass — ✅ Done.** All 5 backend suites verified (auth 38, items
  32, board 37, connectors 13, gateway 17 — Connectors/Gateway never had venvs set up
  before this pass; two real `.env.example` gaps found and fixed, `TWITTER_CLIENT_*` in
  connectors and `CORS_ALLOWED_ORIGINS` in gateway — both read unconditionally at import
  time even when unused, so a fresh clone's tests would fail without them; see
  `daily-startup.md`'s "Per-service venvs and .env" section). Real browser verification via
  Playwright + headless Chromium, confirmed working end to end (owner dashboard, tag
  filtering, logout/login, receiver's read-only board view with genuinely no edit controls
  rendered, zero console errors) — **this sandbox's headless-browser blocker from Phase 2
  is resolved**: system deps (`libnspr4` etc.) are now installed via `sudo npx playwright
  install --with-deps chromium`, run once by the user; reinstall the npm package with
  `npm install --no-save playwright` each session (not saved to `package.json` — it's a
  verification tool, not an app dependency).
- **Manual-testing findings, round 1 — ✅ Done (Decisions #9 partial supersession, #70,
  #71).** Three real gaps found during the user's own click-through: (1) `ShareBar`'s
  "Select all" now disables with zero items instead of being clickable against nothing;
  (2) owner-side board management — `AddItemsToBoardDialog.tsx` (excludes already-on-board
  items from the list, not just from what the server would accept) + a per-item Remove
  button on `BoardPage.tsx`, both owner-only, a Viewer still sees zero controls; (3) the
  receiver's side now shows who shared a board with them (`boards.owner_email`,
  denormalized via Auth's `/me` at creation time — new `services/board/app/auth_client.py`,
  migration `0002_add_owner_email.py` with a one-time backfill for the pre-existing demo
  board). `docs/manual-testing-checklist.md` created so the checklist doesn't need
  re-scrolling chat history each round. All verified live via Playwright against the real
  Phase 4 accounts (add 48→49, remove 49→48, owner_email correct on both display
  locations); 38 Board tests pass.
- **Daily affirmation widget — ✅ Done (Decision #72).** `AffirmationWidget.tsx`, a static
  curated array (~18 entries, safely-attributed quotes + unattributed proverbs + originals,
  no risky misattribution), cycling every 2.5 minutes client-side, never immediately
  repeating. No backend/DB/external API — explicitly declined in favor of the static option
  (same proportionality pattern as Decisions #15/#47/#51). Sits at the top of the
  dashboard, right below the header. Verified: selection logic unit-tested (10k trials, no
  browser needed), real refresh timing confirmed live via Playwright's `page.clock`
  fast-forward rather than actually waiting 2.5 minutes.
- **UI/UX redesign — ✅ Done (Decisions #73–#75).** Full visual rework per
  `docs/study-hub-ui-redesign-spec.md`: `first_name` added to signup/auth (Decision #73,
  nullable, "Welcome back" fallback for pre-existing null-first_name accounts) and
  extended to `boards.owner_first_name` (Decision #74, same denormalize-at-creation
  pattern as `owner_email`); a CSS design-token system, shared `AppLayout`/`AppHeader`/
  `Sidebar` shell replacing the old `.dashboard` markup, a dedicated `/boards` page, and
  restyled Library/Board/auth pages and dialogs (Decision #75). Search, tag popularity,
  source/domain labels, and dashboard stat counts all computed client-side from
  already-loaded data — no new backend endpoints, per the spec's own explicit constraint.
  Responsive down to ~400px. Verified: `tsc -b` clean, lint shows only the two
  pre-existing accepted warnings, full 146-test backend suite passes (Auth/Board/Items/
  Connectors/Gateway), and a live Playwright run against a fresh owner/receiver pair
  confirmed the full redesigned flow end to end (signup-with-name, personalized welcome,
  stat cards, search, tag chips, Add/Edit/Share dialogs, Boards page, owner and viewer
  board pages with correct RBAC-gated controls, unauthorized-board error state, mobile
  layout) — one real mobile header-overlap bug found and fixed during that pass.
- **Invite-to-existing-board — ✅ Done (Decision #76).** A new "Invite" button on the
  owner's `BoardPage.tsx` opens `InviteToBoardDialog.tsx`, letting an owner add another
  person to a board that already exists — previously the only "Share" flow always created
  a brand-new board. No backend change: `POST /{board_id}/invite` already existed and was
  already tested, just never reachable from the UI for an existing board. Verified live:
  Invite button is owner-only, generates a real invite link, and the Boards page
  immediately shows "Shared with 2 people" with the new grant `(pending)`. Follow-up
  (Decision #77): `create_invite` now rejects a second invite to the same email on the
  same board with a `409` ("This board is already shared with that email") unless the
  prior invite expired — closes the duplicate-grant gap Decision #76 itself flagged and
  made newly reachable. 43 Board tests pass; verified live that the friendly error shows
  inline in `InviteToBoardDialog.tsx` without the dialog closing.
- **"Select all" tag/search-filter bug — ✅ Fixed (Decision #78).** User-found bug:
  "Select all" ignored the active tag/search filter and always selected all 70 resources.
  Filter state moved up from `StudyResources.tsx` into `LibraryPage.tsx` (new shared
  `lib/filterResources.ts`), so `ShareBar`'s "Select all" now selects only the
  currently-visible (filtered) items — verified live: filtering to a 3-item tag then
  "Select all" selects exactly 3, not 70; selection persists if the filter is cleared
  afterward. Side effect, noted deliberately: browser-bookmark items are no longer swept
  into "Select all" (previously included via the old unfiltered `items` list) — individual
  bookmark checkboxes are unaffected.
- **Copy-to-clipboard for invite links — ✅ Done (Decision #79).** New shared
  `CopyableLink.tsx`, used by both `ShareDialog.tsx` and `InviteToBoardDialog.tsx`'s "done"
  step — a "Copy" button next to the invite link, swaps to a checkmark + "Copied" for 2s.
  No new infrastructure (no toast system) — just the button's own state. Verified live via
  Playwright with clipboard permissions granted: the exact link lands on the clipboard in
  both dialogs.
- **Tag autocomplete in the resource form — ✅ Done (Decision #80).** As the user types in
  the Tags field, a dropdown suggests matching existing tags (derived client-side from the
  user's own resources, no new endpoint) — matches only the segment after the last comma,
  excludes tags already added, picking one appends `", "` ready for the next tag. Free text
  is still always accepted; suggestions are a convenience, not validation. Verified live
  against the real 70-item/55-tag demo account.
- **"Shared With You" stat card — ✅ Done (Decision #81).** User-found gap: a pure-receiver
  account (owns zero boards, has boards shared with them) saw "0 Your Boards" on the
  Library page with no signal anything was shared — only discoverable via the Boards page.
  Added a 5th stat card, "Shared With You," using the already-existing
  `GET /board/shared-with-me` (no new endpoint). Verified live against both real demo
  accounts: receiver shows "0 Your Boards / 2 Shared With You," owner shows the reverse;
  5-card row confirmed clean at desktop and ~400px mobile.
- **Cosmetic theme pass — ✅ Done (Decisions #82-83).** Welcome subtitle shortened to "Your
  learning library." (dropped an implied subject-matter scope claim). Separately, prompted
  by a mockup the user shared (not a live screenshot — visibly fabricated/dated wrong):
  colored icon-in-circle stat cards, deterministic per-tag chip colors (hashed from the tag
  string, `lib/tagColor.ts` — consistent across Study Resources, the popular-topics filter,
  Add-to-board's dialog, and the tag-suggestions dropdown), a per-row date, a "..." row menu
  replacing the old expand-to-reveal Edit/Delete, a list/grid view toggle, and a small
  floating "corner nudge" card (Library page only, one static message per load, deliberately
  not sharing `AffirmationWidget`'s rotation). Structural/out-of-scope parts of the same
  mockup (global header search, Boards as a sidebar widget, Profile/Settings pages) were
  explicitly discussed and declined — see Decision #83's own reasoning. Verified live
  against the real 70-item demo account across list/grid view, both dialogs, and mobile.
- **Next-stage roadmap — agreed, not yet built.** Full evaluation and phased plan now live
  in `docs/study-hub-architecture.md`'s "Near-Term Direction" section (superseded its
  earlier, now-stale 5-item version). In order: (1) Learning Plans + Continue Learning/This
  Week, new tables in Items' own schema, not a new service; (2) a first real deployment
  pass, pulled forward to right after Phase 1 rather than left until the end — re-verify
  current hosting options/pricing at that point, the old Render note is stale; (3) Learning
  completion/takeaways + Topic-level progress, extending `items` directly via the existing
  `PATCH`; (4) Interview Prep Track — a content decision, not new architecture, using the
  already-curated 70 resources grouped by existing tags; (5) GitHub push, after Phase 1-3
  rather than strictly last — secrets hygiene is already done (Decision #66); (6) Review
  queue + Related resources (client-side, no spaced repetition, no embeddings); (7) Async
  URL metadata enrichment via FastAPI `BackgroundTasks` — no queue/worker/broker. Postgres
  full-text search, Redis, and semantic/vector search are explicitly **not** scheduled —
  reactive only, triggered by a named condition, not built speculatively. Decision Log not
  yet updated for any of this — logged only once each phase is actually implemented.
- **X/Twitter source label + optional Image URL field — ✅ Done (Decision #84).** Prompted
  by a real workflow: saving X/Twitter threads that read like full articles, where the
  images can't be copied as text. `x.com`/`twitter.com`/`chatgpt.com`/`claude.ai` added to
  `lib/sourceLabel.ts`. New optional "Image URL" field on the Add/Edit Resource dialog,
  reusing Items' existing `preview_media_url` column (connectors already populate it;
  manual entry never had access) — no new schema, one PATCH field added. Recommended tag
  convention for these: `ai-help` — needs no code, tags are free-text (Decision #62).
  34 Items tests pass; verified live end to end. **Also:** fixed an unrelated WSL2 Docker
  environment issue blocking `docker compose build` (corrupted `~/.docker/contexts` cache,
  stale `credsStore` pointing at a nonexistent Windows credential helper) — see Decision
  #84's own note for what changed in `~/.docker/config.json`.
