import type { ItemResponse } from "../types/api";
import { useSelection } from "../dashboard/SelectionContext";

interface TwitterTilesProps {
  items: ItemResponse[];
}

// Flat tile grid, no folder concept (Decision #7) — each tile shows
// whatever preview came free with the tweet at ingest time, no extra
// fetching. Clicking opens the original tweet.
export function TwitterTiles({ items }: TwitterTilesProps) {
  const { isSelected, toggle } = useSelection();

  if (items.length === 0) {
    return <p className="empty-state">No tweets synced yet.</p>;
  }

  return (
    <div className="tile-grid">
      {items.map((item) => (
        <div key={item.id} className="tile">
          <input
            type="checkbox"
            className="tile-checkbox"
            checked={isSelected(item.id)}
            onChange={() => toggle(item.id)}
          />
          <a href={item.url} target="_blank" rel="noreferrer">
            {item.preview_media_url && (
              <img className="tile-media" src={item.preview_media_url} alt="" />
            )}
            <p className="tile-text">{item.preview_text ?? item.title}</p>
          </a>
        </div>
      ))}
    </div>
  );
}
