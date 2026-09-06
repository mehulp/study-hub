const notConnectedEl = document.getElementById("not-connected");
const connectedEl = document.getElementById("connected");
const statusEl = document.getElementById("status");
const syncButton = document.getElementById("sync-button");

// Walks the native bookmark tree into the flat list Connectors' /sync
// expects (Decision #44's batch shape). A tree node is either a folder
// (has `children`, no `url`) or an actual bookmark (has `url`, no
// `children`) — never both. folder_path is rebuilt from the ancestor
// folder titles as we descend; the invisible root node has an empty
// title, so it's excluded rather than showing up as an empty path segment.
function flattenBookmarks(nodes, folderPath = []) {
  const items = [];
  for (const node of nodes) {
    if (node.url) {
      items.push({
        external_id: node.id,
        title: node.title || node.url,
        url: node.url,
        folder_path: folderPath.length > 0 ? folderPath.join("/") : null,
        // favicon_url is deliberately omitted — there's no simple,
        // cross-browser way to read a bookmark's favicon from this API;
        // left for the UI to resolve from the URL's own domain later,
        // not something worth solving at ingestion time.
        saved_at: new Date(node.dateAdded).toISOString(),
      });
    } else if (node.children) {
      const nextPath = node.title ? [...folderPath, node.title] : folderPath;
      items.push(...flattenBookmarks(node.children, nextPath));
    }
  }
  return items;
}

async function refreshView() {
  const connection = await getStoredConnection();
  if (connection) {
    connectedEl.hidden = false;
    notConnectedEl.hidden = true;
  } else {
    connectedEl.hidden = true;
    notConnectedEl.hidden = false;
  }
}

document.getElementById("open-options").addEventListener("click", (event) => {
  event.preventDefault();
  browserApi.runtime.openOptionsPage();
});

syncButton.addEventListener("click", async () => {
  const connection = await getStoredConnection();
  if (!connection) {
    statusEl.textContent = "Not connected — set up the connection first.";
    statusEl.className = "error";
    return;
  }

  syncButton.disabled = true;
  statusEl.className = "";
  statusEl.textContent = "Reading bookmarks...";

  try {
    const tree = await browserApi.bookmarks.getTree();
    const items = flattenBookmarks(tree);

    statusEl.textContent = `Syncing ${items.length} bookmarks...`;
    const result = await syncBookmarks(connection.connectionId, connection.pushToken, items);

    const created = result.results.filter((r) => r.status === "created").length;
    const existing = result.results.filter((r) => r.status === "already_exists").length;
    const failed = result.results.filter((r) => r.status === "error").length;

    statusEl.textContent = `Done: ${created} new, ${existing} already synced${failed ? `, ${failed} failed` : ""}.`;
    statusEl.className = failed > 0 ? "error" : "success";
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "error";
  } finally {
    syncButton.disabled = false;
  }
});

refreshView();
