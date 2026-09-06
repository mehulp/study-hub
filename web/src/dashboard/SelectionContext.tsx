import { createContext, useContext, useState, type ReactNode } from "react";

interface SelectionContextValue {
  selectedIds: Set<string>;
  isSelected: (id: string) => boolean;
  toggle: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clear: () => void;
}

const SelectionContext = createContext<SelectionContextValue | null>(null);

// Page-scoped, not global like AuthContext — only wraps the dashboard.
// Exists specifically because FolderTree is recursive and can be several
// levels deep; without this, toggling a checkbox would mean threading a
// callback down through every intermediate folder as props, whether or
// not that folder itself cares. Any tile or row can just call
// useSelection() directly, no matter how deeply nested it is.
export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  function toggle(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function selectAll(ids: string[]) {
    setSelectedIds(new Set(ids));
  }

  function clear() {
    setSelectedIds(new Set());
  }

  return (
    <SelectionContext.Provider
      value={{ selectedIds, isSelected: (id) => selectedIds.has(id), toggle, selectAll, clear }}
    >
      {children}
    </SelectionContext.Provider>
  );
}

export function useSelection(): SelectionContextValue {
  const context = useContext(SelectionContext);
  if (!context) {
    throw new Error("useSelection must be used within a SelectionProvider");
  }
  return context;
}
