// InterviewPal practice packs a plan can be paired with, and the links that open them.
//
// The pairing is saved on the plan (learning_plans.interviewpal_pack_keys, edited in the plan form): an ordered list, so a
// week can have several daily practice sessions, one pack each. It stores the packs' stable KEYS, never their display
// names, so renaming a pack or a plan breaks nothing. The supported options are explicit here and in the backend (items
// service, schemas.InterviewPalPackKey): to add a pack, add it in both places and ship the pack in InterviewPal
// (src/packs.js). The shared contract is in docs/interviewpal-integration.md.

export interface PracticePack {
  key: string; // what is stored, and what the link carries as ?pack=
  label: string; // the full name, in the plan form
  shortLabel: string; // on the plan page's buttons
}

// In the order they are offered (and saved).
export const PRACTICE_PACKS: PracticePack[] = [
  { key: "system-design-consistent-hashing", label: "System Design — Consistent Hashing", shortLabel: "Consistent hashing" },
  { key: "system-design-cap-consistency", label: "System Design — CAP and Consistency", shortLabel: "CAP and consistency" },
  { key: "system-design-week-1", label: "System Design — Week 1 (mixed review)", shortLabel: "Week 1 review" },
];

export const packByKey = (key: string): PracticePack | null => PRACTICE_PACKS.find((pack) => pack.key === key) ?? null;
export const isSupportedPack = (key: string): boolean => packByKey(key) !== null;

// Where InterviewPal runs. Read when the app is built (Vite), like VITE_GATEWAY_URL. If VITE_INTERVIEWPAL_URL is unset
// or blank the default depends on the build: `npm run dev` points at local InterviewPal, a production build (`npm run
// build`, which is what a hosted deploy runs) points at the published one, so a deploy works without extra settings.
//   local dev  http://localhost:8010/                  (where scripts/interviewpal.sh serves it)
//   hosted     https://mehulp.github.io/interview-pal/ (keep the base path, and the trailing slash)
// Set VITE_INTERVIEWPAL_URL in web/.env.local (local runs) or as a build variable (a hosted build) to override either.
const DEFAULT_INTERVIEWPAL_URL = import.meta.env.PROD ? "https://mehulp.github.io/interview-pal/" : "http://localhost:8010/";
const INTERVIEWPAL_URL: string = import.meta.env.VITE_INTERVIEWPAL_URL || DEFAULT_INTERVIEWPAL_URL;

export interface PracticeLink {
  pack: PracticePack;
  url: string;
}

// One link per supported saved pack, in the saved order. Unsupported keys and a badly written base URL give no link (show
// nothing rather than a broken button). InterviewPal gets the pack key and the plan ID, and builds its own way back from
// the plan ID. The link contract stays one pack per link.
export function practiceLinksFor(plan: { id: string; interviewpal_pack_keys: string[] }): PracticeLink[] {
  const links: PracticeLink[] = [];
  for (const key of plan.interviewpal_pack_keys ?? []) {
    const pack = packByKey(key);
    if (!pack) continue;
    try {
      const url = new URL(INTERVIEWPAL_URL); // keeps any base path
      if (!url.pathname.endsWith("/")) url.pathname += "/";
      url.search = "";
      url.hash = "";
      url.searchParams.set("pack", pack.key);
      url.searchParams.set("plan", plan.id.toLowerCase());
      links.push({ pack, url: url.toString() });
    } catch {
      return [];
    }
  }
  return links;
}
