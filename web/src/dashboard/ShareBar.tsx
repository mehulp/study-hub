import { useState } from "react";
import { useSelection } from "./SelectionContext";
import { ShareDialog } from "./ShareDialog";

interface ShareBarProps {
  allItemIds: string[];
  onShared?: () => void;
}

// Journey 3: "select all, then deselect unwanted ones, or pick individual
// items one at a time" — selectAll seeds the full set for the first path,
// individual checkboxes (in StudyResources/FolderTree) handle both.
export function ShareBar({ allItemIds, onShared }: ShareBarProps) {
  const { selectedIds, selectAll, clear } = useSelection();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="share-bar">
      <span>{selectedIds.size} selected</span>
      <button onClick={() => selectAll(allItemIds)} disabled={allItemIds.length === 0}>
        Select all
      </button>
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
            // Lets the new board show up under "Boards I've Shared" right
            // away — a brand-new board always has an invite created in the
            // same flow (Decision #9), so it belongs there immediately.
            onShared?.();
          }}
        />
      )}
    </div>
  );
}
