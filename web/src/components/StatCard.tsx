import type { ReactNode } from "react";

type StatCardTone = "purple" | "amber" | "blue" | "pink" | "gray";

interface StatCardProps {
  value: number;
  label: string;
  icon: ReactNode;
  tone: StatCardTone;
}

// Never hardcoded (redesign spec section 13) -- every caller derives
// `value` from already-loaded data (resources.length, a Set of tags, etc.),
// not a new statistics endpoint. Icon + tone are purely cosmetic (Decision
// #83) -- a fixed, deterministic pairing per card, not derived from data.
export function StatCard({ value, label, icon, tone }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className={`stat-card-icon stat-card-icon-${tone}`}>{icon}</div>
      <div>
        <div className="stat-card-value">{value}</div>
        <div className="stat-card-label">{label}</div>
      </div>
    </div>
  );
}
