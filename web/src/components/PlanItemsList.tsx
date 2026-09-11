import type { PlanItemResponse, PlanItemStatus, Priority } from "../types/api";
import { resolveSourceInfo } from "../lib/sourceLabel";
import { tagHueClass } from "../lib/tagColor";
import { EmptyState } from "./EmptyState";

interface PlanItemsListProps {
  items: PlanItemResponse[];
  onStatusChange: (itemId: string, status: PlanItemStatus) => void;
  onPriorityChange: (itemId: string, priority: Priority | null) => void;
  onTargetDateChange: (itemId: string, targetDate: string | null) => void;
  onRemove: (itemId: string) => void;
}

const STATUS_LABELS: Record<PlanItemStatus, string> = {
  not_started: "Not Started",
  in_progress: "In Progress",
  completed: "Completed",
  skipped: "Skipped",
};

// Ordering, priority, and target date are all real columns already
// (Decision #85), but this first pass only surfaces status + priority +
// target date -- drag-to-reorder and an effort-estimate input are real UI
// work of their own, deliberately left for a later pass rather than
// bundled into an already-large first cut.
export function PlanItemsList({
  items,
  onStatusChange,
  onPriorityChange,
  onTargetDateChange,
  onRemove,
}: PlanItemsListProps) {
  if (items.length === 0) {
    return <EmptyState title="Nothing in this plan yet." />;
  }

  return (
    <div className="plan-items-list">
      {items.map((item) => {
        const source = resolveSourceInfo(item.url);
        return (
          <div key={item.item_id} className={`plan-item-row plan-item-status-${item.status}`}>
            <div className="plan-item-main">
              <a href={item.url} target="_blank" rel="noreferrer" className="resource-title">
                {item.title}
              </a>
              <div className="resource-source-label">{source.label}</div>
              {item.tags.length > 0 && (
                <div className="resource-tags">
                  {item.tags.map((tag) => (
                    <span key={tag} className={`tag-chip tag-chip-small ${tagHueClass(tag)}`}>
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="plan-item-controls">
              <select
                className="plan-item-status-select"
                value={item.status}
                onChange={(e) => onStatusChange(item.item_id, e.target.value as PlanItemStatus)}
                aria-label={`Status for ${item.title}`}
              >
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <select
                value={item.priority ?? ""}
                onChange={(e) => onPriorityChange(item.item_id, (e.target.value || null) as Priority | null)}
                aria-label={`Priority for ${item.title}`}
              >
                <option value="">No priority</option>
                <option value="low">Low priority</option>
                <option value="medium">Medium priority</option>
                <option value="high">High priority</option>
              </select>
              <input
                type="date"
                value={item.target_date ?? ""}
                onChange={(e) => onTargetDateChange(item.item_id, e.target.value || null)}
                aria-label={`Target date for ${item.title}`}
              />
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => onRemove(item.item_id)}
              >
                Remove
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
