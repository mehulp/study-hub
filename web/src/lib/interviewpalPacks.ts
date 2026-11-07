// InterviewPal practice packs a plan can be paired with, and the link that opens one.
//
// The pairing is saved on the plan (learning_plans.interviewpal_pack_key, edited in the plan form). It stores the pack's
// stable KEY, never its display name, so renaming a pack or a plan breaks nothing. The supported options are explicit
// here and in the backend (items service, schemas.InterviewPalPackKey): to add a pack, add it in both places and ship
// the pack in InterviewPal (src/packs.js). The shared contract is in docs/interviewpal-integration.md.

export interface PracticePack {
  key: string; // what is stored, and what the link carries as ?pack=
  label: string; // what people see
}

export const PRACTICE_PACKS: PracticePack[] = [{ key: "system-design-week-1", label: "System Design — Week 1" }];

export function packLabel(key: string | null | undefined): string | null {
  if (!key) return null;
  return PRACTICE_PACKS.find((pack) => pack.key === key)?.label ?? null;
}

export const isSupportedPack = (key: string | null | undefined): boolean => packLabel(key) !== null;

// Where InterviewPal runs. Read when the app is built (Vite), like VITE_GATEWAY_URL. If VITE_INTERVIEWPAL_URL is unset
// or blank the default depends on the build: `npm run dev` points at local InterviewPal, a production build (`npm run
// build`, which is what a hosted deploy runs) points at the published one, so a deploy works without extra settings.
//   local dev  http://localhost:8010/                  (where scripts/interviewpal.sh serves it)
//   hosted     https://mehulp.github.io/interview-pal/ (keep the base path, and the trailing slash)
// Set VITE_INTERVIEWPAL_URL in web/.env.local (local runs) or as a build variable (a hosted build) to override either.
const DEFAULT_INTERVIEWPAL_URL = import.meta.env.PROD ? "https://mehulp.github.io/interview-pal/" : "http://localhost:8010/";
const INTERVIEWPAL_URL: string = import.meta.env.VITE_INTERVIEWPAL_URL || DEFAULT_INTERVIEWPAL_URL;

// The InterviewPal address for a plan with a supported saved pairing, or null (no pairing, an unsupported key, or a badly
// written base URL: show no button rather than a broken one). InterviewPal gets the pack key and the plan ID, and builds
// its own way back from the plan ID.
export function practiceLinkFor(plan: { id: string; interviewpal_pack_key: string | null }): string | null {
  if (!isSupportedPack(plan.interviewpal_pack_key)) return null;
  try {
    const url = new URL(INTERVIEWPAL_URL); // keeps any base path
    if (!url.pathname.endsWith("/")) url.pathname += "/";
    url.search = "";
    url.hash = "";
    url.searchParams.set("pack", plan.interviewpal_pack_key as string);
    url.searchParams.set("plan", plan.id.toLowerCase());
    return url.toString();
  } catch {
    return null;
  }
}
