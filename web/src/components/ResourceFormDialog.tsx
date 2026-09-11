import { useState, type FormEvent } from "react";
import { createItem, updateItem } from "../api/items";
import type { ItemResponse } from "../types/api";

interface ResourceFormDialogProps {
  item?: ItemResponse; // present = edit mode, absent = create mode
  onClose: () => void;
  onSaved: (item: ItemResponse) => void;
}

function parseTags(text: string): string[] {
  return text
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
}

// Same dialog for create and edit (Decision #64 built PATCH specifically so
// editing wasn't a second, separate flow to design) — `item` being present
// is the only thing that switches which API call submit makes.
export function ResourceFormDialog({ item, onClose, onSaved }: ResourceFormDialogProps) {
  const isEdit = item !== undefined;
  const [title, setTitle] = useState(item?.title ?? "");
  const [url, setUrl] = useState(item?.url ?? "");
  const [notes, setNotes] = useState(item?.notes ?? "");
  const [tagsText, setTagsText] = useState(item?.tags.join(", ") ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const tags = parseTags(tagsText);
      const saved = isEdit
        ? await updateItem(item.id, { title, url, notes: notes || null, tags })
        : await createItem({ title, url, notes: notes || null, tags });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-labelledby="resource-form-title">
        <h3 id="resource-form-title">{isEdit ? "Edit resource" : "Add a study resource"}</h3>
        <form onSubmit={handleSubmit}>
          <label className="field">
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required disabled={saving} />
          </label>
          <label className="field">
            URL
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              disabled={saving}
            />
          </label>
          <label className="field">
            Notes
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={saving}
              rows={3}
            />
          </label>
          <label className="field">
            Tags
            <span className="dialog-hint">Separate tags with commas.</span>
            <input
              value={tagsText}
              onChange={(e) => setTagsText(e.target.value)}
              disabled={saving}
              placeholder="system-design, distributed-systems"
            />
          </label>
          {error && <p className="error">{error}</p>}
          <div className="dialog-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving..." : isEdit ? "Save changes" : "Add resource"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
