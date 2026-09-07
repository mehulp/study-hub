import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { listItems } from "../api/items";
import { getTwitterAuthorizeUrl } from "../api/twitter";
import type { ItemResponse } from "../types/api";
import { TwitterTiles } from "../components/TwitterTiles";
import { BrowserBookmarks } from "../components/BrowserBookmarks";
import { SelectionProvider } from "../dashboard/SelectionContext";
import { ShareBar } from "../dashboard/ShareBar";

export function DashboardPage() {
  const { logout } = useAuth();
  const [items, setItems] = useState<ItemResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Connectors' /twitter/callback redirects here with this query param on
  // success (Connectors itself has no page of its own to land on) — read
  // once on mount, then strip it so a page refresh doesn't keep showing it.
  const [justConnectedTwitter] = useState(
    () => new URLSearchParams(window.location.search).get("twitter") === "connected"
  );

  useEffect(() => {
    if (justConnectedTwitter) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, [justConnectedTwitter]);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load items"));
  }, []);

  async function handleConnectTwitter() {
    try {
      window.location.href = await getTwitterAuthorizeUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Twitter connection");
    }
  }

  const twitterItems = items?.filter((item) => item.source === "twitter") ?? [];
  const browserItems = items?.filter((item) => item.source !== "twitter") ?? [];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Bookmarks Hub</h1>
        <button onClick={() => logout()}>Log out</button>
      </header>

      {error && <p className="error">{error}</p>}
      {justConnectedTwitter && <p className="success">Twitter connected.</p>}
      {!items && !error && <p>Loading...</p>}

      {items && (
        <SelectionProvider>
          <ShareBar allItemIds={items.map((item) => item.id)} />
          <section>
            <div className="section-header">
              <h2>Twitter</h2>
              <button onClick={handleConnectTwitter}>Connect Twitter</button>
            </div>
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
