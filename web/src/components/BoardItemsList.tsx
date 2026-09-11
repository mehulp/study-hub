import type { BoardItemResponse } from "../types/api";
import { resolveFaviconUrl } from "../lib/favicon";

interface BoardItemsListProps {
  items: BoardItemResponse[];
  // Present only for the owner — a viewer gets the same list with no way
  // to change it (Decision #10).
  onRemove?: (itemId: string) => void;
}

// Board never stores an item's source or folder (Decision #37's
// denormalized snapshot only keeps display fields), so there's no
// source-specific tile/list split here the way the dashboard has —
// just one flat list, honest to what's actually stored.
export function BoardItemsList({ items, onRemove }: BoardItemsListProps) {
  if (items.length === 0) {
    return <p className="empty-state">This board has no items yet.</p>;
  }

  return (
    <div className="board-items-list">
      {items.map((item) => (
        <div key={item.item_id} className="board-item-row">
          <a
            className="board-item-link"
            href={item.url}
            target="_blank"
            rel="noreferrer"
          >
            {item.preview_media_url ? (
              <img className="board-item-media" src={item.preview_media_url} alt="" />
            ) : (
              <img className="favicon" src={resolveFaviconUrl(item)} alt="" />
            )}
            <div>
              <p className="board-item-title">{item.title}</p>
              {item.preview_text && <p className="board-item-preview">{item.preview_text}</p>}
              <span className="bookmark-url">{item.url}</span>
            </div>
          </a>
          {onRemove && (
            <button className="board-item-remove" onClick={() => onRemove(item.item_id)}>
              Remove
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
