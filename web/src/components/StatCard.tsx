interface StatCardProps {
  value: number;
  label: string;
}

// Never hardcoded (redesign spec section 13) -- every caller derives
// `value` from already-loaded data (resources.length, a Set of tags, etc.),
// not a new statistics endpoint.
export function StatCard({ value, label }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card-value">{value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}
