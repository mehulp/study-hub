import { useEffect, useState } from "react";
import { listItems } from "../api/items";
import { addPlanItem } from "../api/plans";
import type { ItemResponse } from "../types/api";
import { tagHueClass } from "../lib/tagColor";

interface AddItemsToPlanDialogProps {
  planId: string;
  planName: string;
  existingItemIds: Set<string>;
  onClose: () => void;
  onAdded: () => void;
}

// Same shape as AddItemsToBoardDialog -- items already on this plan are
// excluded from the list entirely, not just blocked server-side (same
// reasoning as Decision #70).
export function AddItemsToPlanDialog({
  planId,
  planName,
  existingItemIds,
  onClose,
  onAdded,
}: AddItemsToPlanDialogProps) {
  const [items, setItems] = useState<ItemResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filterText, setFilterText] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch(() => setError("We couldn't load your resources. Please try again."));
  }, []);

  const addableItems = (items ?? []).filter((item) => !existingItemIds.has(item.id));
  const needle = filterText.trim().toLowerCase();
  const visibleItems = needle
    ? addableItems.filter((item) => item.title.toLowerCase().includes(needle))
    : addableItems;

  function toggle(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleAdd() {
    setSaving(true);
    setError(null);
    try {
      for (const id of selectedIds) {
        await addPlanItem(planId, { item_id: id });
      }
      onAdded();
      onClose();
    } catch {
      setError("We couldn't add those resources. Please try again.");
      setSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog dialog-wide" role="dialog" aria-labelledby="add-items-to-plan-title">
        <h3 id="add-items-to-plan-title">Add resources to "{planName}"</h3>

        {error && <p className="error">{error}</p>}
        {!items && !error && <p className="loading-state">Loading resources...</p>}

        {items && addableItems.length === 0 && (
          <p className="empty-state">Every one of your resources is already on this plan.</p>
        )}

        {items && addableItems.length > 0 && (
          <>
            <input
              type="search"
              placeholder="Search resources..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              disabled={saving}
              aria-label="Search resources"
            />
            <div className="add-items-list">
              {visibleItems.map((item) => (
                <label key={item.id} className="add-items-row">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={() => toggle(item.id)}
                    disabled={saving}
                  />
                  <div>
                    {item.title}
                    {item.tags.length > 0 && (
                      <div className="add-items-row-tags">
                        {item.tags.map((tag) => (
                          <span key={tag} className={`tag-chip tag-chip-small ${tagHueClass(tag)}`}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </label>
              ))}
            </div>
          </>
        )}

        <div className="dialog-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAdd}
            disabled={saving || selectedIds.size === 0}
          >
            {saving ? "Adding..." : `Add ${selectedIds.size} resource${selectedIds.size === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>
    </div>
  );
}
