import { useState, type FormEvent } from "react";
import { createItem, updateItem } from "../api/items";
import type { ItemResponse } from "../types/api";
import { tagDotClass } from "../lib/tagColor";

interface ResourceFormDialogProps {
  item?: ItemResponse; // present = edit mode, absent = create mode
  existingTags: string[]; // for the tag-suggestions dropdown, not validation -- any text is still a valid tag
  onClose: () => void;
  onSaved: (item: ItemResponse) => void;
}

function parseTags(text: string): string[] {
  return text
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
}

// Tags are comma-separated in one plain input (Decision #62's free-text
// design), so "what's being typed right now" is just whatever's after the
// last comma -- suggestions match against that segment alone, not the
// whole field, and picking one replaces just that segment.
function activeTagSegment(text: string): string {
  const lastComma = text.lastIndexOf(",");
  return (lastComma === -1 ? text : text.slice(lastComma + 1)).trim();
}

function applyTagSuggestion(text: string, suggestion: string): string {
  const lastComma = text.lastIndexOf(",");
  const prefix = lastComma === -1 ? "" : `${text.slice(0, lastComma + 1)} `;
  return `${prefix}${suggestion}, `;
}

// Same dialog for create and edit (Decision #64 built PATCH specifically so
// editing wasn't a second, separate flow to design) — `item` being present
// is the only thing that switches which API call submit makes.
export function ResourceFormDialog({ item, existingTags, onClose, onSaved }: ResourceFormDialogProps) {
  const isEdit = item !== undefined;
  const [title, setTitle] = useState(item?.title ?? "");
  const [url, setUrl] = useState(item?.url ?? "");
  const [notes, setNotes] = useState(item?.notes ?? "");
  const [imageUrl, setImageUrl] = useState(item?.preview_media_url ?? "");
  const [tagsText, setTagsText] = useState(item?.tags.join(", ") ?? "");
  const [tagsFocused, setTagsFocused] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSegment = activeTagSegment(tagsText);
  const lastComma = tagsText.lastIndexOf(",");
  const completedTagsLower = (lastComma === -1 ? [] : parseTags(tagsText.slice(0, lastComma))).map((tag) =>
    tag.toLowerCase(),
  );
  const tagSuggestions =
    tagsFocused && activeSegment.length > 0
      ? existingTags
          .filter(
            (tag) =>
              tag.toLowerCase().startsWith(activeSegment.toLowerCase()) &&
              !completedTagsLower.includes(tag.toLowerCase()),
          )
          .slice(0, 6)
      : [];

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const tags = parseTags(tagsText);
      const saved = isEdit
        ? await updateItem(item.id, {
            title,
            url,
            notes: notes || null,
            imageUrl: imageUrl.trim() || null,
            tags,
          })
        : await createItem({ title, url, notes: notes || null, imageUrl: imageUrl.trim() || null, tags });
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
            Image URL
            <span className="dialog-hint">
              Optional. A direct link to an image (e.g. from a tweet you can't copy as text).
            </span>
            <input
              type="url"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              disabled={saving}
              placeholder="https://pbs.twimg.com/media/..."
            />
          </label>
          <label className="field">
            Tags
            <span className="dialog-hint">Separate tags with commas.</span>
            <div className="tag-input-wrap">
              <input
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
                onFocus={() => setTagsFocused(true)}
                onBlur={() => setTagsFocused(false)}
                disabled={saving}
                placeholder="system-design, distributed-systems"
                autoComplete="off"
              />
              {tagSuggestions.length > 0 && (
                <div className="tag-suggestions" role="listbox">
                  {tagSuggestions.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      className="tag-suggestion"
                      role="option"
                      aria-selected={false}
                      // mousedown (not click/onClick) fires before the input's
                      // blur, so the dropdown doesn't close out from under the
                      // click and the suggestion still applies correctly.
                      onMouseDown={(e) => {
                        e.preventDefault();
                        setTagsText(applyTagSuggestion(tagsText, tag));
                      }}
                    >
                      <span className={`tag-suggestion-dot ${tagDotClass(tag)}`} aria-hidden="true" />
                      {tag}
                    </button>
                  ))}
                </div>
              )}
            </div>
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
