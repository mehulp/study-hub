import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

// Intentional compact cards (redesign spec section 34) instead of plain
// italic text -- no illustrations, just a title, an optional sentence, and
// an optional action.
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state-card">
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}
