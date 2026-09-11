import { useEffect, useMemo, useState } from "react";
import { listItems } from "../api/items";
import { addItemToBoard } from "../api/board";
import type { ItemResponse } from "../types/api";

interface AddItemsToBoardDialogProps {
  boardId: string;
  existingItemIds: Set<string>;
  onClose: () => void;
  onAdded: () => void;
}

// Reopens what Decision #9 originally deferred ("add selection to an
// existing board") — items already on this board are excluded from the
// list entirely, not just prevented server-side, so there's nothing
// confusing to even attempt selecting (Board's own add-item endpoint is
// already idempotent either way, Decision #33's pattern, but a duplicate
// checkbox in a picker is a UX bug even if the backend would shrug it off).
export function AddItemsToBoardDialog({
  boardId,
  existingItemIds,
  onClose,
  onAdded,
}: AddItemsToBoardDialogProps) {
  const [items, setItems] = useState<ItemResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filterText, setFilterText] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load resources"));
  }, []);

  const addableItems = useMemo(() => {
    if (!items) return [];
    return items.filter((item) => !existingItemIds.has(item.id));
  }, [items, existingItemIds]);

  const visibleItems = useMemo(() => {
    const needle = filterText.trim().toLowerCase();
    if (!needle) return addableItems;
    return addableItems.filter((item) => item.title.toLowerCase().includes(needle));
  }, [addableItems, filterText]);

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
        await addItemToBoard(boardId, id);
      }
      onAdded();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add items");
      setSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog dialog-wide">
        <h3>Add resources to this board</h3>

        {error && <p className="error">{error}</p>}
        {!items && !error && <p>Loading...</p>}

        {items && addableItems.length === 0 && (
          <p className="empty-state">Every one of your resources is already on this board.</p>
        )}

        {items && addableItems.length > 0 && (
          <>
            <input
              type="text"
              placeholder="Filter by title..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              disabled={saving}
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
                  {item.title}
                </label>
              ))}
            </div>
          </>
        )}

        <div className="dialog-actions">
          <button type="button" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            type="button"
            onClick={handleAdd}
            disabled={saving || selectedIds.size === 0}
          >
            {saving ? "Adding..." : `Add ${selectedIds.size || ""} Selected`}
          </button>
        </div>
      </div>
    </div>
  );
}
