import type { BoardItemResponse } from "../types/api";
import { resolveFaviconUrl } from "../lib/favicon";

interface BoardItemsListProps {
  items: BoardItemResponse[];
}

// Board never stores an item's source or folder (Decision #37's
// denormalized snapshot only keeps display fields), so there's no
// source-specific tile/list split here the way the dashboard has —
// just one flat list, honest to what's actually stored.
export function BoardItemsList({ items }: BoardItemsListProps) {
  if (items.length === 0) {
    return <p className="empty-state">This board has no items yet.</p>;
  }

  return (
    <div className="board-items-list">
      {items.map((item) => (
        <a
          key={item.item_id}
          className="board-item-row"
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
      ))}
    </div>
  );
}
