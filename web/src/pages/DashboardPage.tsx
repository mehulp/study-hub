import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { listItems, deleteItem } from "../api/items";
import { listMyBoards, listSharedWithMe } from "../api/board";
import type { ItemResponse, OwnedBoardResponse, SharedBoardResponse } from "../types/api";
import { StudyResources } from "../components/StudyResources";
import { ResourceFormDialog } from "../components/ResourceFormDialog";
import { BrowserBookmarks } from "../components/BrowserBookmarks";
import { MyBoards } from "../components/MyBoards";
import { SharedWithMe } from "../components/SharedWithMe";
import { AffirmationWidget } from "../components/AffirmationWidget";
import { SelectionProvider } from "../dashboard/SelectionContext";
import { ShareBar } from "../dashboard/ShareBar";

// null = closed, "new" = create mode, an item = edit mode for that item.
type FormTarget = ItemResponse | "new" | null;

export function DashboardPage() {
  const { logout } = useAuth();
  const [items, setItems] = useState<ItemResponse[] | null>(null);
  const [myBoards, setMyBoards] = useState<OwnedBoardResponse[] | null>(null);
  const [sharedBoards, setSharedBoards] = useState<SharedBoardResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formTarget, setFormTarget] = useState<FormTarget>(null);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load items"));
    listMyBoards()
      .then(setMyBoards)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load your boards"));
    listSharedWithMe()
      .then(setSharedBoards)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load shared boards"));
  }, []);

  function handleSaved(saved: ItemResponse) {
    setItems((current) => {
      if (!current) return current;
      const exists = current.some((item) => item.id === saved.id);
      return exists ? current.map((item) => (item.id === saved.id ? saved : item)) : [saved, ...current];
    });
  }

  async function handleDelete(item: ItemResponse) {
    if (!window.confirm(`Delete "${item.title}"? This can't be undone.`)) return;
    try {
      await deleteItem(item.id);
      setItems((current) => current?.filter((existing) => existing.id !== item.id) ?? current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  // Browser-synced items (chrome/firefox, via the extension) keep their own
  // folder-tree view — folder_path is a genuinely different concept from
  // tags (Decision #62), still dormant pending the capture-extension rework
  // (Decision #60), not dropped. Everything else (source="manual" today) is
  // the primary, tag-browsable resource list.
  const manualItems = items?.filter((item) => item.source === "manual") ?? [];
  const browserItems = items?.filter((item) => item.source !== "manual") ?? [];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Mehul's Study Hub</h1>
        <button onClick={() => logout()}>Log out</button>
      </header>

      <AffirmationWidget />

      {error && <p className="error">{error}</p>}
      {!items && !error && <p>Loading...</p>}

      {items && (
        <SelectionProvider>
          <ShareBar
            allItemIds={items.map((item) => item.id)}
            onShared={() => listMyBoards().then(setMyBoards).catch(() => {})}
          />
          <section>
            <div className="section-header">
              <h2>Study Resources</h2>
              <button onClick={() => setFormTarget("new")}>Add Resource</button>
            </div>
            <StudyResources
              items={manualItems}
              onEdit={(item) => setFormTarget(item)}
              onDelete={handleDelete}
            />
          </section>
          <section>
            <h2>Browser Bookmarks</h2>
            <BrowserBookmarks items={browserItems} />
          </section>
        </SelectionProvider>
      )}

      {myBoards && (
        <section>
          <h2>Boards I've Shared</h2>
          <MyBoards boards={myBoards} />
        </section>
      )}

      {sharedBoards && (
        <section>
          <h2>Shared With Me</h2>
          <SharedWithMe boards={sharedBoards} />
        </section>
      )}

      {formTarget && (
        <ResourceFormDialog
          item={formTarget === "new" ? undefined : formTarget}
          onClose={() => setFormTarget(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
