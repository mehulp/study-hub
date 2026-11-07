# Study Hub ↔ InterviewPal integration

The shared contract lives in InterviewPal's repo as `docs/study-hub-integration.md`; this page is the Study Hub side and must agree with it.

## What it does

A learning plan can be paired with an InterviewPal practice pack. In the plan form (create or edit) choose **InterviewPal practice pack**: **None** or **System Design — Week 1**. A plan with a pack shows **Practise in InterviewPal** under its heading. The button opens InterviewPal with the pack selected; **Back to study plan** in InterviewPal returns to the same plan.

## The saved pairing

- Column: `items.learning_plans.interviewpal_pack_key` (text, nullable). It holds the pack's **stable key** (`system-design-week-1`), never its label.
- Migration: `services/items/alembic/versions/0004_add_plan_interviewpal_pack_key.py`. It only adds a nullable column, so existing plans load with no pairing. The items container runs `alembic upgrade head` when it starts, so rebuilding and restarting it applies the migration.
- API (items service, behind the gateway at `/items/plans`):
  - `POST /plans` accepts `interviewpal_pack_key` (a supported key or null/omitted).
  - `PATCH /plans/{id}`: **omit** the field to keep the saved pairing, send **null** to remove it, send a supported key to set it. Same partial-update rule as `description`.
  - Supported keys are the explicit `Literal` in `services/items/app/schemas.py` (`InterviewPalPackKey`). Anything else is rejected with 422 and nothing changes. The check is in the API, not a database constraint, so adding a pack is a code change and not another migration.
  - Responses include `interviewpal_pack_key` (null when unpaired). Ownership is unchanged: another user's plan is a 404, so they cannot read or change its pairing.
- The same pack can be paired with any number of plans.

## The frontend

- Supported options: `web/src/lib/interviewpalPacks.ts` (`PRACTICE_PACKS`: key and label). Keep it equal to the backend list.
- The selector is in `web/src/components/PlanFormDialog.tsx`; the button is in `web/src/pages/PlanDetailPage.tsx`.
- Base URL of InterviewPal: `VITE_INTERVIEWPAL_URL`, read at build time (see `web/.env.example`).
  - If unset or blank, the default depends on the build: `npm run dev` uses `http://localhost:8010/`, a production build (`npm run build`, what a hosted deploy runs) uses `https://mehulp.github.io/interview-pal/`. So a hosted deploy needs no extra setting.
  - To override either, set `VITE_INTERVIEWPAL_URL` (keep the base path and the trailing slash): in `web/.env.local` for local runs, or as a build variable (Cloudflare Workers Builds → Variables) for a hosted build.
- The earlier one-plan pilot setting `VITE_PILOT_PLAN_ID` is gone; remove it from `web/.env.local` if it is there.

## Local verification steps

1. Apply the migration to the local database: rebuild and restart the items service (`bash scripts/studyhub.sh restart --build`, or `docker compose up -d --build items`). Check: `docker compose exec postgres psql -U study_hub -d study_hub -c "\d items.learning_plans"` shows `interviewpal_pack_key`.
2. Backend tests (uses the separate `study_hub_test` database): `cd services/items && ./venv/bin/python -m pytest -q`.
3. Frontend: `cd web && npm run lint && npm run build`.
4. Start InterviewPal (`scripts/interviewpal.sh start`, port 8010) and Study Hub (5173). Edit a plan, choose the pack, save, click **Practise in InterviewPal**, add the question set, choose a mode, Start, finish, then **Back to study plan**. Remove the pairing with **None**: the button disappears.

## Hosted release

Deploy order: (1) deploy the items service (its start command runs the migration); (2) build Study Hub (a production build already defaults to the hosted InterviewPal address); (3) InterviewPal needs no setting, but its trusted Study Hub origins (`STUDY_HUB_ORIGINS` in `src/packs.js`) must match the deployed Study Hub address. Rolling back the app does not need a database rollback: the column is optional and older code ignores it.
