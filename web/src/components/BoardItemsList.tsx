import type { BoardItemResponse } from "../types/api";
import { resolveFaviconUrl } from "../lib/favicon";
import { resolveSourceInfo } from "../lib/sourceLabel";
import { EmptyState } from "./EmptyState";
import { PlusIcon, CheckIcon } from "../lib/icons";

interface BoardItemsListProps {
  items: BoardItemResponse[];
  // Present only for the owner — a viewer gets the same list with no way
  // to change it (Decision #10).
  onRemove?: (itemId: string) => void;
  // Present only for a non-owner viewer (Decision #89) — the owner already
  // owns every item on their own board, so there's nothing to save.
  onSaveToLibrary?: (item: BoardItemResponse) => void;
  // URLs already in the viewer's own Library, checked eagerly (same
  // pre-filter pattern as AddItemsToBoardDialog, Decision #70) so "already
  // saved" shows as a disabled checkmark rather than failing after a click.
  savedUrls?: Set<string>;
}

// Board never stores an item's source or folder (Decision #37's
// denormalized snapshot only keeps display fields), so there's no
// source-specific tile/list split here the way the Library has —
// just one flat list, honest to what's actually stored. Source labels
// (section 18) are still derived client-side from the URL, same as
// Study Resources.
export function BoardItemsList({ items, onRemove, onSaveToLibrary, savedUrls }: BoardItemsListProps) {
  if (items.length === 0) {
    return <EmptyState title="This board has no items yet." />;
  }

  return (
    <div className="board-items-list">
      {items.map((item) => {
        const source = resolveSourceInfo(item.url);
        return (
          <div key={item.item_id} className="board-item-row">
            <a className="board-item-link" href={item.url} target="_blank" rel="noreferrer">
              {item.preview_media_url ? (
                <img className="board-item-media" src={item.preview_media_url} alt="" />
              ) : (
                <img className="favicon" src={resolveFaviconUrl(item)} alt="" />
              )}
              <div>
                <p className="board-item-title">{item.title}</p>
                {item.preview_text && <p className="board-item-preview">{item.preview_text}</p>}
                <span className="board-item-source">{source.label}</span>
              </div>
            </a>
            {onRemove && (
              <button className="btn btn-danger btn-sm" onClick={() => onRemove(item.item_id)}>
                Remove
              </button>
            )}
            {onSaveToLibrary &&
              (savedUrls?.has(item.url) ? (
                <button className="btn btn-secondary btn-sm" disabled>
                  <CheckIcon size={14} />
                  Saved
                </button>
              ) : (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSaveToLibrary(item)}
                >
                  <PlusIcon size={14} />
                  Save to My Resources
                </button>
              ))}
          </div>
        );
      })}
    </div>
  );
}
