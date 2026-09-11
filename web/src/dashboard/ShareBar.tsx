import { useState } from "react";
import { useSelection } from "./SelectionContext";
import { ShareDialog } from "./ShareDialog";

interface ShareBarProps {
  allItemIds: string[];
}

// Journey 3: "select all, then deselect unwanted ones, or pick individual
// items one at a time" — selectAll seeds the full set for the first path,
// individual checkboxes (in StudyResources/FolderTree) handle both.
export function ShareBar({ allItemIds }: ShareBarProps) {
  const { selectedIds, selectAll, clear } = useSelection();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="share-bar">
      <span>{selectedIds.size} selected</span>
      <button onClick={() => selectAll(allItemIds)}>Select all</button>
      <button onClick={clear} disabled={selectedIds.size === 0}>
        Clear
      </button>
      <button disabled={selectedIds.size === 0} onClick={() => setDialogOpen(true)}>
        Share selected
      </button>

      {dialogOpen && (
        <ShareDialog
          itemIds={Array.from(selectedIds)}
          onClose={() => setDialogOpen(false)}
          onShared={() => {
            clear();
          }}
        />
      )}
    </div>
  );
}
