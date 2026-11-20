# Study Hub ↔ InterviewPal integration

The shared contract lives in InterviewPal's repo as `docs/study-hub-integration.md`; this page is the Study Hub side and must agree with it.

## What it does

A learning plan can be paired with an InterviewPal practice pack. In the plan form (create or edit) choose **InterviewPal practice pack**: **None** or **System Design — Week 1**. A plan with a pack shows **Practise in InterviewPal** under its heading. The button opens InterviewPal with the pack selected; **Back to study plan** in InterviewPal returns to the same plan.

## The saved pairing

- Column: `items.learning_plans.interviewpal_pack_keys` (JSONB array of text, NOT NULL, default `[]`): the **stable keys** of the packs the plan is paired with, in order (never labels). Several packs per plan means several daily sessions for a week.
- Migrations (items service): `0004` added a single key; `0005` adds the list and carries existing single pairings over. The old single-key column is **kept** (expand-only) and the application keeps it equal to the first pack, so the previous release still works against the new schema. Existing plans load with an empty list. The items container runs `alembic upgrade head` when it starts, so rebuilding and restarting it applies them.
- API (items service, behind the gateway at `/items/plans`):
  - `POST /plans` accepts `interviewpal_pack_keys` (a list of supported keys, no repeats; omitted = none).
  - `PATCH /plans/{id}`: **omit** the field to keep the saved pairing, send **`[]`** (or null) to remove it, send a list of supported keys to set it. Same partial-update rule as `description`.
  - Supported keys are the explicit `Literal` in `services/items/app/schemas.py` (`InterviewPalPackKey`). Anything else, or a repeated key, is rejected with 422 and nothing changes. The check is in the API, not a database constraint, so adding a pack is a code change and not another migration.
  - Responses include `interviewpal_pack_keys` (and, deprecated, `interviewpal_pack_key`, the first of the list). The old single-key request form (`interviewpal_pack_key`) is still accepted as a list of one, so a frontend from before 0005 keeps working during a deploy; it can be removed once that frontend is gone.
  - Ownership is unchanged: another user's plan is a 404, so they cannot read or change its pairing.
- The same pack can be paired with any number of plans.

## The frontend

- Supported options and their order: `web/src/lib/interviewpalPacks.ts` (`PRACTICE_PACKS`: key, label, short label). Keep it equal to the backend list and to InterviewPal's `src/packs.js`.
- The pack checkboxes are in `web/src/components/PlanFormDialog.tsx`; the buttons (one per saved pack, or "Practise in InterviewPal" when there is just one) are in `web/src/pages/PlanDetailPage.tsx`. A plan with a pack and no resources still shows its buttons, with a one-line hint underneath.
- Base URL of InterviewPal: `VITE_INTERVIEWPAL_URL`, read at build time (see `web/.env.example`).
  - If unset or blank, the default depends on the build: `npm run dev` uses `http://localhost:8010/`, a production build (`npm run build`, what a hosted deploy runs) uses `https://mehulp.github.io/interview-pal/`. So a hosted deploy needs no extra setting.
  - To override either, set `VITE_INTERVIEWPAL_URL` (keep the base path and the trailing slash): in `web/.env.local` for local runs, or as a build variable (Cloudflare Workers Builds → Variables) for a hosted build.
- The earlier one-plan pilot setting `VITE_PILOT_PLAN_ID` is gone; remove it from `web/.env.local` if it is there.

## Local verification steps

1. Apply the migration to the local database: rebuild and restart the items service (`bash scripts/studyhub.sh restart --build`, or `docker compose up -d --build items`). Check: `docker compose exec postgres psql -U study_hub -d study_hub -c "\d items.learning_plans"` shows `interviewpal_pack_key`.
2. Backend tests (uses the separate `study_hub_test` database; start Postgres first: `docker compose up -d postgres`): `cd services/items && ./venv/bin/python -m pytest -q`. A test run occasionally fails with a 401 from the token check (an existing intermittent problem, unrelated to plans): rerun it.
3. Frontend: `cd web && npm run lint && npm run build`.
4. Start InterviewPal (`scripts/interviewpal.sh start`, port 8010) and Study Hub (5173). Edit a plan, tick one or more packs, save, click a **Practise** button, add the question set, choose a mode, Start, finish, then **Back to study plan** and do the next pack. Untick the packs to remove the pairing: the buttons disappear.

## Hosted release

Deploy order, and why it is safe at every step:
1. **Study Hub backend** (the items service; its start command runs the migrations). The new backend still accepts the old single-key request form and still returns the old single-key field, so the frontend that is live at this point keeps working.
2. **InterviewPal** (push to GitHub Pages). It accepts every link the old frontend produces; its trusted Study Hub origins (`STUDY_HUB_ORIGINS` in its `src/packs.js`) must match the deployed Study Hub address.
3. **Study Hub frontend** (a production build already defaults to the hosted InterviewPal address). Its pack buttons only appear once InterviewPal can handle them.

Rollback: migration `0005` only adds the list column and the application keeps the old single-key column equal to the first pack (expand-only), so rolling the items service back to the release before `0005` needs no database change (and rolling forward again does not lose a pairing the older release wrote: a plan whose list is empty but whose single-key column is set still shows that pack). Rolling the frontend back after plans have several packs shows only the first pack's button, and saving a plan from that old form would keep only that pack, so avoid editing plans on a rolled-back frontend. Drop the old column in a later migration, only once no release before `0005` can run again.
