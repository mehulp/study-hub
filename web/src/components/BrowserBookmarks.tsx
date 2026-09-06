import type { ItemResponse, Source } from "../types/api";
import { buildFolderTree } from "../lib/folderTree";
import { FolderTree } from "./FolderTree";

interface BrowserBookmarksProps {
  items: ItemResponse[];
}

const BROWSER_SOURCES: { source: Source; label: string }[] = [
  { source: "chrome", label: "Chrome" },
  { source: "firefox", label: "Firefox" },
];

// Chrome and Firefox are separate, unsynced bookmark stores (Decision #7),
// so each gets its own top-level section and its own folder tree — never
// merged into one.
export function BrowserBookmarks({ items }: BrowserBookmarksProps) {
  const bySource = BROWSER_SOURCES.map(({ source, label }) => ({
    label,
    items: items.filter((item) => item.source === source),
  })).filter((group) => group.items.length > 0);

  if (bySource.length === 0) {
    return <p className="empty-state">No browser bookmarks synced yet.</p>;
  }

  return (
    <div className="browser-bookmarks">
      {bySource.map(({ label, items: sourceItems }) => {
        // The tree's root is a synthetic empty-name wrapper (there's no
        // real "no folder" folder) — render its children directly rather
        // than the root itself, which would otherwise show an unnamed
        // folder header wrapping everything.
        const root = buildFolderTree(sourceItems);
        const topLevelFolders = Array.from(root.children.values()).sort((a, b) =>
          a.name.localeCompare(b.name)
        );
        return (
          <div key={label} className="browser-source">
            <h3>{label}</h3>
            {topLevelFolders.map((folder) => (
              <FolderTree key={folder.path} node={folder} />
            ))}
          </div>
        );
      })}
    </div>
  );
}
