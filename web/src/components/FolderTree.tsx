import { useState } from "react";
import type { FolderNode } from "../lib/folderTree";
import { resolveFaviconUrl } from "../lib/favicon";
import { useSelection } from "../dashboard/SelectionContext";

interface FolderTreeProps {
  node: FolderNode;
  defaultExpanded?: boolean;
}

// One folder's worth of rendering — its own bookmarks plus, recursively,
// each subfolder. Every folder manages its own expand/collapse state
// independently, so opening one doesn't affect its siblings.
export function FolderTree({ node, defaultExpanded = false }: FolderTreeProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const { isSelected, toggle } = useSelection();
  const childFolders = Array.from(node.children.values()).sort((a, b) =>
    a.name.localeCompare(b.name)
  );
  const hasContent = node.items.length > 0 || childFolders.length > 0;

  if (!hasContent) return null;

  return (
    <div className="folder-node">
      <button className="folder-header" onClick={() => setExpanded((e) => !e)}>
        <span className="folder-arrow">{expanded ? "▾" : "▸"}</span>
        📁 {node.name}
      </button>
      {expanded && (
        <div className="folder-body">
          {node.items.map((item) => (
            <div key={item.id} className="bookmark-row">
              <input
                type="checkbox"
                checked={isSelected(item.id)}
                onChange={() => toggle(item.id)}
              />
              <a href={item.url} target="_blank" rel="noreferrer" className="bookmark-link">
                <img className="favicon" src={resolveFaviconUrl(item)} alt="" />
                <span className="bookmark-title">{item.title}</span>
                <span className="bookmark-url">{item.url}</span>
              </a>
            </div>
          ))}
          {childFolders.map((child) => (
            <FolderTree key={child.path} node={child} />
          ))}
        </div>
      )}
    </div>
  );
}
