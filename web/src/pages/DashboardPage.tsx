import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { listItems } from "../api/items";
import type { ItemResponse } from "../types/api";
import { TwitterTiles } from "../components/TwitterTiles";
import { BrowserBookmarks } from "../components/BrowserBookmarks";
import { SelectionProvider } from "../dashboard/SelectionContext";
import { ShareBar } from "../dashboard/ShareBar";

export function DashboardPage() {
  const { logout } = useAuth();
  const [items, setItems] = useState<ItemResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load items"));
  }, []);

  const twitterItems = items?.filter((item) => item.source === "twitter") ?? [];
  const browserItems = items?.filter((item) => item.source !== "twitter") ?? [];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Bookmarks Hub</h1>
        <button onClick={() => logout()}>Log out</button>
      </header>

      {error && <p className="error">{error}</p>}
      {!items && !error && <p>Loading...</p>}

      {items && (
        <SelectionProvider>
          <ShareBar allItemIds={items.map((item) => item.id)} />
          <section>
            <h2>Twitter</h2>
            <TwitterTiles items={twitterItems} />
          </section>
          <section>
            <h2>Browser Bookmarks</h2>
            <BrowserBookmarks items={browserItems} />
          </section>
        </SelectionProvider>
      )}
    </div>
  );
}
