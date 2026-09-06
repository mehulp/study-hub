import type { ItemResponse } from "../types/api";

export interface FolderNode {
  name: string;
  path: string;
  children: Map<string, FolderNode>;
  items: ItemResponse[];
}

function makeNode(name: string, path: string): FolderNode {
  return { name, path, children: new Map(), items: [] };
}

// folder_path is a "/"-joined ancestor chain (e.g. "Bookmarks Bar/Work"),
// rebuilt client-side by the extension at sync time — an item's folder_path
// names the folder it's directly inside, never a subfolder of its own,
// since items are always leaves. Items with no folder_path (shouldn't
// happen for a real browser sync, but the schema allows it) land in a
// synthetic "Uncategorized" bucket at the root instead of being dropped.
export function buildFolderTree(items: ItemResponse[]): FolderNode {
  const root = makeNode("", "");

  for (const item of items) {
    const segments = item.folder_path ? item.folder_path.split("/") : ["Uncategorized"];

    let node = root;
    let path = "";
    for (const segment of segments) {
      path = path ? `${path}/${segment}` : segment;
      let child = node.children.get(segment);
      if (!child) {
        child = makeNode(segment, path);
        node.children.set(segment, child);
      }
      node = child;
    }
    node.items.push(item);
  }

  return root;
}
