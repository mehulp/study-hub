import { useMemo, useState } from "react";
import type { ItemResponse } from "../types/api";
import { useSelection } from "../dashboard/SelectionContext";

interface StudyResourcesProps {
  items: ItemResponse[];
  onEdit: (item: ItemResponse) => void;
  onDelete: (item: ItemResponse) => void;
}

// Tags are multi-valued (Decision #62), so — unlike the old Twitter/Browser
// split — items can't be filed into one fixed section each. A flat list with
// tag-chip filters fits the actual shape of the data: click a tag to narrow,
// click it again to clear.
export function StudyResources({ items, onEdit, onDelete }: StudyResourcesProps) {
  const { isSelected, toggle } = useSelection();
  const [activeTag, setActiveTag] = useState<string | null>(null);
  // Collapsed by default -- only ids in this set are expanded. At real
  // scale (70 items in the seeded demo account) showing every row's notes
  // and Edit/Delete buttons at once turns the page into mostly scrolling,
  // not reading. Tags stay visible either way so you can still scan/filter
  // without expanding anything.
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  function toggleExpanded(id: string) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    for (const item of items) {
      for (const tag of item.tags) tags.add(tag);
    }
    return Array.from(tags).sort();
  }, [items]);

  if (items.length === 0) {
    return <p className="empty-state">No study resources yet — add one above.</p>;
  }

  const visibleItems = activeTag ? items.filter((item) => item.tags.includes(activeTag)) : items;

  return (
    <div className="study-resources">
      {allTags.length > 0 && (
        <div className="tag-filter">
          <button
            className={activeTag === null ? "tag-chip tag-chip-active" : "tag-chip"}
            onClick={() => setActiveTag(null)}
          >
            All ({items.length})
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              className={activeTag === tag ? "tag-chip tag-chip-active" : "tag-chip"}
              onClick={() => setActiveTag(activeTag === tag ? null : tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      <div className="resource-list">
        {visibleItems.map((item) => {
          const expanded = expandedIds.has(item.id);
          return (
            <div key={item.id} className="resource-row">
              <input
                type="checkbox"
                checked={isSelected(item.id)}
                onChange={() => toggle(item.id)}
              />
              <div className="resource-body">
                <div className="resource-header">
                  <button
                    className="resource-toggle"
                    onClick={() => toggleExpanded(item.id)}
                    aria-label={expanded ? "Collapse" : "Expand"}
                    aria-expanded={expanded}
                  >
                    {expanded ? "▾" : "▸"}
                  </button>
                  <a href={item.url} target="_blank" rel="noreferrer" className="resource-title">
                    {item.title}
                  </a>
                </div>
                {item.tags.length > 0 && (
                  <div className="resource-tags">
                    {item.tags.map((tag) => (
                      <span key={tag} className="tag-chip tag-chip-small">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                {expanded && item.notes && <p className="resource-notes">{item.notes}</p>}
              </div>
              {expanded && (
                <div className="resource-actions">
                  <button onClick={() => onEdit(item)}>Edit</button>
                  <button onClick={() => onDelete(item)}>Delete</button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
