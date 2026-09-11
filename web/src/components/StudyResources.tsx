import { useState } from "react";
import type { ItemResponse } from "../types/api";
import { useSelection } from "../dashboard/SelectionContext";
import { resolveSourceInfo, type ResourceKind } from "../lib/sourceLabel";
import { tagHueClass } from "../lib/tagColor";
import { formatDate } from "../lib/formatDate";
import { ArticleIcon, VideoIcon, LinkIcon, DotsIcon, ListIcon, GridIcon } from "../lib/icons";
import type { SortOption } from "../lib/filterResources";
import { EmptyState } from "./EmptyState";

interface StudyResourcesProps {
  items: ItemResponse[];
  // Already filtered (by activeTag/searchQuery) and sorted by the parent,
  // via the same `filterAndSortResources` LibraryPage uses to scope
  // ShareBar's "Select all" — kept as a single shared source of truth
  // rather than each place computing its own idea of "visible".
  visibleItems: ItemResponse[];
  activeTag: string | null;
  onActiveTagChange: (tag: string | null) => void;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  sortBy: SortOption;
  onSortByChange: (sort: SortOption) => void;
  onEdit: (item: ItemResponse) => void;
  onDelete: (item: ItemResponse) => void;
  onAddFirst: () => void;
}

const POPULAR_TAG_COUNT = 8;
type ViewMode = "list" | "grid";

function SourceIcon({ kind }: { kind: ResourceKind }) {
  if (kind === "video") return <VideoIcon className="resource-source-icon" size={16} />;
  if (kind === "article") return <ArticleIcon className="resource-source-icon" size={16} />;
  return <LinkIcon className="resource-source-icon" size={16} />;
}

function kindLabel(kind: ResourceKind): string {
  if (kind === "video") return "Video";
  if (kind === "article") return "Article";
  return "Link";
}

// The "..." action menu (Decision #83, replacing the old expand-to-reveal
// Edit/Delete buttons) -- shared between list and grid rows so Edit/Delete
// are always one click away, not gated behind expanding a row first.
function ResourceMenu({
  open,
  onToggle,
  onEdit,
  onDelete,
}: {
  open: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="row-menu-wrap">
      <button
        type="button"
        className="row-menu-toggle"
        aria-label="Resource actions"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={onToggle}
      >
        <DotsIcon size={18} />
      </button>
      {open && (
        <div className="row-menu" role="menu">
          <button role="menuitem" onClick={onEdit}>
            Edit
          </button>
          <button role="menuitem" className="row-menu-danger" onClick={onDelete}>
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

// Tags are multi-valued (Decision #62), so — unlike the old Twitter/Browser
// split — items can't be filed into one fixed section each. A flat list
// with tag-chip filters fits the actual shape of the data. Search, sort,
// and the popular-topics computation are all client-side, derived from the
// `items` this component is already given — no new backend endpoint
// (redesign spec section 46).
export function StudyResources({
  items,
  visibleItems,
  activeTag,
  onActiveTagChange,
  searchQuery,
  onSearchQueryChange,
  sortBy,
  onSortByChange,
  onEdit,
  onDelete,
  onAddFirst,
}: StudyResourcesProps) {
  const { isSelected, toggle } = useSelection();
  const [tagPanelOpen, setTagPanelOpen] = useState(false);
  const [tagSearch, setTagSearch] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  // Collapsed by default -- only ids in this set are expanded. At real
  // scale (70 items in the seeded demo account) showing every row's notes
  // at once turns the page into mostly scrolling, not reading. Tags stay
  // visible either way so you can still scan/filter without expanding
  // anything. Grid view has no expand/notes at all -- it's the compact
  // overview mode, Edit/Delete/notes stay one click (or a view switch) away.
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  function toggleExpanded(id: string) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleMenu(id: string) {
    setOpenMenuId((current) => (current === id ? null : id));
  }

  if (items.length === 0) {
    return (
      <EmptyState
        title="No study resources yet"
        description="Save articles, videos and system-design references so your learning material stays in one place."
        action={
          <button className="btn btn-primary" onClick={onAddFirst}>
            + Add your first resource
          </button>
        }
      />
    );
  }

  // Popularity computed client-side from the resources actually loaded
  // (redesign spec section 15) -- ties broken alphabetically for a stable
  // order rather than depending on Map iteration order.
  const tagCounts = new Map<string, number>();
  for (const item of items) {
    for (const tag of item.tags) tagCounts.set(tag, (tagCounts.get(tag) ?? 0) + 1);
  }
  const allTagsByPopularity = Array.from(tagCounts.keys()).sort(
    (a, b) => (tagCounts.get(b) ?? 0) - (tagCounts.get(a) ?? 0) || a.localeCompare(b)
  );
  const popularTags = allTagsByPopularity.slice(0, POPULAR_TAG_COUNT);
  const hasMoreTags = allTagsByPopularity.length > POPULAR_TAG_COUNT;
  const tagPanelResults = tagSearch.trim()
    ? allTagsByPopularity.filter((tag) => tag.toLowerCase().includes(tagSearch.trim().toLowerCase()))
    : allTagsByPopularity;
  // The active tag might not be one of the "popular" ones (picked from the
  // full list via "+ More") -- always show it as a chip even if it'd
  // otherwise fall outside the top N, so there's no way to have an active
  // filter with no visible way to see or clear it.
  const visibleTagChips =
    activeTag && !popularTags.includes(activeTag) ? [...popularTags, activeTag] : popularTags;

  return (
    <div className="study-resources">
      <div className="field" style={{ marginBottom: 16 }}>
        <input
          type="search"
          className="resource-search"
          placeholder="Search resources, notes or tags..."
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          aria-label="Search resources, notes or tags"
        />
      </div>

      <div className="tag-filter">
        <button
          className={activeTag === null ? "tag-chip tag-chip-active" : "tag-chip"}
          onClick={() => onActiveTagChange(null)}
        >
          All ({items.length})
        </button>
        {visibleTagChips.map((tag) => (
          <button
            key={tag}
            className={
              activeTag === tag ? "tag-chip tag-chip-active" : `tag-chip ${tagHueClass(tag)}`
            }
            onClick={() => onActiveTagChange(activeTag === tag ? null : tag)}
          >
            {tag}
          </button>
        ))}
        {hasMoreTags && (
          <button className="tag-chip" onClick={() => setTagPanelOpen((open) => !open)}>
            {tagPanelOpen ? "− Fewer" : "+ More"}
          </button>
        )}
      </div>

      {tagPanelOpen && (
        <div className="tag-more-panel">
          <input
            type="search"
            placeholder="Search topics..."
            value={tagSearch}
            onChange={(e) => setTagSearch(e.target.value)}
            aria-label="Search topics"
          />
          <div className="tag-more-list">
            {tagPanelResults.map((tag) => (
              <button
                key={tag}
                className={
                  activeTag === tag ? "tag-chip tag-chip-active" : `tag-chip ${tagHueClass(tag)}`
                }
                onClick={() => {
                  onActiveTagChange(activeTag === tag ? null : tag);
                  setTagPanelOpen(false);
                }}
              >
                {tag} ({tagCounts.get(tag)})
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="resource-toolbar-row">
        <div className="sort-select">
          Sort by:
          <select value={sortBy} onChange={(e) => onSortByChange(e.target.value as SortOption)}>
            <option value="recent">Recently added</option>
            <option value="title">Title A–Z</option>
          </select>
        </div>
        <div className="view-toggle">
          <button
            type="button"
            className={`view-toggle-btn${viewMode === "list" ? " active" : ""}`}
            onClick={() => setViewMode("list")}
            aria-label="List view"
            aria-pressed={viewMode === "list"}
          >
            <ListIcon size={16} />
          </button>
          <button
            type="button"
            className={`view-toggle-btn${viewMode === "grid" ? " active" : ""}`}
            onClick={() => setViewMode("grid")}
            aria-label="Grid view"
            aria-pressed={viewMode === "grid"}
          >
            <GridIcon size={16} />
          </button>
        </div>
      </div>

      {visibleItems.length === 0 ? (
        <p className="empty-state">No resources match your search and filters.</p>
      ) : viewMode === "grid" ? (
        <div className="resource-grid">
          {visibleItems.map((item) => {
            const source = resolveSourceInfo(item.url);
            return (
              <div key={item.id} className={`resource-card${isSelected(item.id) ? " selected" : ""}`}>
                <div className="resource-card-top">
                  <input
                    type="checkbox"
                    checked={isSelected(item.id)}
                    onChange={() => toggle(item.id)}
                    aria-label={`Select ${item.title}`}
                  />
                  <ResourceMenu
                    open={openMenuId === item.id}
                    onToggle={() => toggleMenu(item.id)}
                    onEdit={() => {
                      onEdit(item);
                      setOpenMenuId(null);
                    }}
                    onDelete={() => {
                      onDelete(item);
                      setOpenMenuId(null);
                    }}
                  />
                </div>
                <div className="resource-header">
                  <SourceIcon kind={source.kind} />
                  <div className="resource-title-group">
                    <a href={item.url} target="_blank" rel="noreferrer" className="resource-title">
                      {item.title}
                    </a>
                    <div className="resource-source-label">
                      {source.label} · {kindLabel(source.kind)}
                    </div>
                  </div>
                </div>
                {item.tags.length > 0 && (
                  <div className="resource-tags">
                    {item.tags.map((tag) => (
                      <span key={tag} className={`tag-chip tag-chip-small ${tagHueClass(tag)}`}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <span className="resource-card-date">{formatDate(item.saved_at)}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="resource-list">
          {visibleItems.map((item) => {
            const expanded = expandedIds.has(item.id);
            const source = resolveSourceInfo(item.url);
            return (
              <div key={item.id} className={`resource-row${isSelected(item.id) ? " selected" : ""}`}>
                <input
                  type="checkbox"
                  checked={isSelected(item.id)}
                  onChange={() => toggle(item.id)}
                  aria-label={`Select ${item.title}`}
                />
                <div className="resource-body">
                  <div className="resource-header">
                    <button
                      className="resource-toggle"
                      onClick={() => toggleExpanded(item.id)}
                      aria-label={expanded ? "Collapse" : "Expand"}
                      aria-expanded={expanded}
                    >
                      {expanded ? "▾" : "▸"}
                    </button>
                    <SourceIcon kind={source.kind} />
                    <div className="resource-title-group">
                      <a href={item.url} target="_blank" rel="noreferrer" className="resource-title">
                        {item.title}
                      </a>
                      <div className="resource-source-label">
                        {source.label} · {kindLabel(source.kind)}
                      </div>
                    </div>
                  </div>
                  {item.tags.length > 0 && (
                    <div className="resource-tags">
                      {item.tags.map((tag) => (
                        <span key={tag} className={`tag-chip tag-chip-small ${tagHueClass(tag)}`}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {expanded && (
                    <>
                      {item.notes && (
                        <>
                          <div className="resource-source-label" style={{ marginTop: 10 }}>
                            Notes
                          </div>
                          <p className="resource-notes">{item.notes}</p>
                        </>
                      )}
                      <a href={item.url} target="_blank" rel="noreferrer" className="resource-open-link">
                        Open resource ↗
                      </a>
                    </>
                  )}
                </div>
                <div className="resource-meta">
                  <span className="resource-date">{formatDate(item.saved_at)}</span>
                  <ResourceMenu
                    open={openMenuId === item.id}
                    onToggle={() => toggleMenu(item.id)}
                    onEdit={() => {
                      onEdit(item);
                      setOpenMenuId(null);
                    }}
                    onDelete={() => {
                      onDelete(item);
                      setOpenMenuId(null);
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
