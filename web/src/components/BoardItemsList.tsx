import type { BoardItemResponse } from "../types/api";
import { resolveFaviconUrl } from "../lib/favicon";
import { resolveSourceInfo } from "../lib/sourceLabel";
import { EmptyState } from "./EmptyState";

interface BoardItemsListProps {
  items: BoardItemResponse[];
  // Present only for the owner — a viewer gets the same list with no way
  // to change it (Decision #10).
  onRemove?: (itemId: string) => void;
}

// Board never stores an item's source or folder (Decision #37's
// denormalized snapshot only keeps display fields), so there's no
// source-specific tile/list split here the way the Library has —
// just one flat list, honest to what's actually stored. Source labels
// (section 18) are still derived client-side from the URL, same as
// Study Resources.
export function BoardItemsList({ items, onRemove }: BoardItemsListProps) {
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
          </div>
        );
      })}
    </div>
  );
}
