import type { ItemResponse } from "../types/api";

export type SortOption = "recent" | "title";

export interface ResourceFilter {
  activeTag: string | null;
  searchQuery: string;
  sortBy: SortOption;
}

// Shared between StudyResources (what to render) and LibraryPage (what
// "Select all" should select) so the two can't silently disagree about
// which items are currently "visible" — the bug that let "Select all"
// grab every resource regardless of the active tag/search filter.
export function filterAndSortResources(items: ItemResponse[], filter: ResourceFilter): ItemResponse[] {
  const searchNeedle = filter.searchQuery.trim().toLowerCase();
  const filtered = items.filter((item) => {
    if (filter.activeTag && !item.tags.includes(filter.activeTag)) return false;
    if (!searchNeedle) return true;
    let hostname = "";
    try {
      hostname = new URL(item.url).hostname;
    } catch {
      // malformed URL -- hostname search just won't match, title/notes/tags still can
    }
    return (
      item.title.toLowerCase().includes(searchNeedle) ||
      hostname.toLowerCase().includes(searchNeedle) ||
      (item.notes ?? "").toLowerCase().includes(searchNeedle) ||
      item.tags.some((tag) => tag.toLowerCase().includes(searchNeedle))
    );
  });
  return filter.sortBy === "title"
    ? [...filtered].sort((a, b) => a.title.localeCompare(b.title))
    : filtered; // "recent": already the order Items' own API returns (saved_at desc)
}
