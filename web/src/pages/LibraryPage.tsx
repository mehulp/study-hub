import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { listItems, deleteItem } from "../api/items";
import { listMyBoards, listSharedWithMe } from "../api/board";
import { listPlans } from "../api/plans";
import type { ItemResponse, OwnedBoardResponse, PlanResponse, SharedBoardResponse } from "../types/api";
import { AppLayout } from "../layout/AppLayout";
import { StudyResources } from "../components/StudyResources";
import { ResourceFormDialog } from "../components/ResourceFormDialog";
import { BrowserBookmarks } from "../components/BrowserBookmarks";
import { AffirmationWidget } from "../components/AffirmationWidget";
import { StatCard } from "../components/StatCard";
import { CornerNudge } from "../components/CornerNudge";
import { ContinueLearning } from "../components/ContinueLearning";
import { SelectionProvider } from "../dashboard/SelectionContext";
import { ShareBar } from "../dashboard/ShareBar";
import { filterAndSortResources, type SortOption } from "../lib/filterResources";
import { BookIcon, TagIcon, BoardsIcon, UsersIcon, LinkIcon } from "../lib/icons";

// null = closed, "new" = create mode, an item = edit mode for that item.
type FormTarget = ItemResponse | "new" | null;

export function LibraryPage() {
  const { currentUser } = useAuth();
  const location = useLocation();
  const [items, setItems] = useState<ItemResponse[] | null>(null);
  const [myBoards, setMyBoards] = useState<OwnedBoardResponse[] | null>(null);
  const [sharedBoards, setSharedBoards] = useState<SharedBoardResponse[] | null>(null);
  const [plans, setPlans] = useState<PlanResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formTarget, setFormTarget] = useState<FormTarget>(null);
  // Owned here (not inside StudyResources) so ShareBar's "Select all" can
  // be scoped to the same "currently visible" set the list itself is
  // showing — previously "Select all" grabbed every resource regardless
  // of the active tag/search filter, since the toolbar and the filter
  // state lived in disconnected components.
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("recent");

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch(() => setError("We couldn't load your resources. Please try again."));
    listMyBoards()
      .then(setMyBoards)
      .catch(() => setError("We couldn't load your boards. Please try again."));
    listSharedWithMe()
      .then(setSharedBoards)
      .catch(() => setError("We couldn't load boards shared with you. Please try again."));
    listPlans()
      .then(setPlans)
      .catch(() => setError("We couldn't load your plans. Please try again."));
  }, []);

  // Cross-page triggers, both using the same navigation-state mechanism
  // ProtectedRoute already established for its own `from` state: the
  // header's "+ Add Resource" (from any page) and the sidebar's "Browser
  // Bookmarks" (scrolls to that section rather than being its own route,
  // redesign spec section 8). This genuinely is synchronizing with an
  // external system (react-router's location state, which changes even
  // without remounting this component when the header link is clicked
  // while already on "/") — the oxlint set-state-in-effect warning here is
  // a known false positive, accepted deliberately rather than "fixed" into
  // a useState initializer, which would silently stop reacting to repeat
  // triggers from the same route (verified live: it broke the header
  // button when already on the Library page).
  useEffect(() => {
    const state = location.state as { openAddDialog?: boolean; scrollTo?: string } | null;
    if (state?.openAddDialog) {
      setFormTarget("new");
    }
    if (state?.scrollTo) {
      document.getElementById(state.scrollTo)?.scrollIntoView({ behavior: "smooth" });
    }
    if (state?.openAddDialog || state?.scrollTo) {
      window.history.replaceState({}, "");
    }
  }, [location.state]);

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
  const uniqueTopicCount = new Set(manualItems.flatMap((item) => item.tags)).size;
  const visibleManualItems = filterAndSortResources(manualItems, { activeTag, searchQuery, sortBy });
  const existingTags = Array.from(new Set(manualItems.flatMap((item) => item.tags))).sort();

  return (
    <AppLayout>
      <div className="page-heading">
        <h1>{currentUser?.first_name ? `Welcome back, ${currentUser.first_name}!` : "Welcome back"}</h1>
        <p>Your learning library.</p>
      </div>

      <AffirmationWidget />

      {error && <p className="error">{error}</p>}
      {!items && !error && <p className="loading-state">Loading resources...</p>}

      {items && (
        <>
          <div className="stat-cards">
            <StatCard
              value={manualItems.length}
              label="Study Resources"
              icon={<BookIcon size={20} />}
              tone="purple"
            />
            <StatCard
              value={uniqueTopicCount}
              label="Unique Topics"
              icon={<TagIcon size={20} />}
              tone="amber"
            />
            <StatCard
              value={myBoards?.length ?? 0}
              label="Your Boards"
              icon={<BoardsIcon size={20} />}
              tone="blue"
              to="/boards"
            />
            <StatCard
              value={sharedBoards?.length ?? 0}
              label="Shared With You"
              icon={<UsersIcon size={20} />}
              tone="pink"
              to="/boards"
            />
            <StatCard
              value={browserItems.length}
              label="Browser Bookmarks"
              icon={<LinkIcon size={20} />}
              tone="gray"
            />
          </div>

          {plans && <ContinueLearning plans={plans} />}

          <SelectionProvider>
            <ShareBar
              allItemIds={visibleManualItems.map((item) => item.id)}
              onShared={() => listMyBoards().then(setMyBoards).catch(() => {})}
            />
            <section className="dashboard-section">
              <div className="section-header">
                <h2 className="section-heading">Study Resources ({manualItems.length})</h2>
              </div>
              <StudyResources
                items={manualItems}
                visibleItems={visibleManualItems}
                activeTag={activeTag}
                onActiveTagChange={setActiveTag}
                searchQuery={searchQuery}
                onSearchQueryChange={setSearchQuery}
                sortBy={sortBy}
                onSortByChange={setSortBy}
                onEdit={(item) => setFormTarget(item)}
                onDelete={handleDelete}
                onAddFirst={() => setFormTarget("new")}
              />
            </section>
            <section className="dashboard-section sources-section" id="browser-bookmarks">
              <h2 className="section-heading">Sources / Integrations</h2>
              <BrowserBookmarks items={browserItems} />
            </section>
          </SelectionProvider>
        </>
      )}

      {formTarget && (
        <ResourceFormDialog
          item={formTarget === "new" ? undefined : formTarget}
          existingTags={existingTags}
          onClose={() => setFormTarget(null)}
          onSaved={handleSaved}
        />
      )}

      <CornerNudge />
    </AppLayout>
  );
}
