import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type StatCardTone = "purple" | "amber" | "blue" | "pink" | "gray";

interface StatCardProps {
  value: number;
  label: string;
  icon: ReactNode;
  tone: StatCardTone;
  // Optional -- only the two board-related cards pass this (Decision #95,
  // revisiting #81's "keep every card non-clickable for row consistency").
  // They have a real nav target (/boards); Study Resources/Unique
  // Topics/Browser Bookmarks don't, so they stay plain divs.
  to?: string;
}

// Never hardcoded (redesign spec section 13) -- every caller derives
// `value` from already-loaded data (resources.length, a Set of tags, etc.),
// not a new statistics endpoint. Icon + tone are purely cosmetic (Decision
// #83) -- a fixed, deterministic pairing per card, not derived from data.
export function StatCard({ value, label, icon, tone, to }: StatCardProps) {
  const content = (
    <>
      <div className={`stat-card-icon stat-card-icon-${tone}`}>{icon}</div>
      <div>
        <div className="stat-card-value">{value}</div>
        <div className="stat-card-label">{label}</div>
      </div>
    </>
  );
  if (to) {
    return (
      <Link to={to} className="stat-card stat-card-link">
        {content}
      </Link>
    );
  }
  return <div className="stat-card">{content}</div>;
}
