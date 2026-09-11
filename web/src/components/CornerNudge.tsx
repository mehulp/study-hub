import { useState } from "react";

// A small, separate floating card, distinct from the top AffirmationWidget
// (Decision #72) -- a fixed message per mount (picked once, not a second
// independent rotation timer) so it can't coincidentally show the same or a
// contradicting quote next to the top widget at the same time. Purely
// decorative (Decision #83), Library page only -- hidden below ~900px via
// CSS so it doesn't compete for space with the mobile layout.
const NUDGES: { icon: string; text: string }[] = [
  { icon: "💡", text: "Small, steady steps outlast bursts of intensity. Keep going!" },
  { icon: "🎯", text: "One resource at a time. You've already started." },
  { icon: "🧠", text: "Every topic you tag is one less thing to relearn later." },
  { icon: "🚀", text: "Consistency beats cramming. Come back tomorrow." },
];

export function CornerNudge() {
  const [nudge] = useState(() => NUDGES[Math.floor(Math.random() * NUDGES.length)]);

  return (
    <div className="corner-nudge">
      <span className="corner-nudge-icon" aria-hidden="true">
        {nudge.icon}
      </span>
      <p className="corner-nudge-text">{nudge.text}</p>
    </div>
  );
}
