import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getBoard, removeItemFromBoard } from "../api/board";
import type { BoardWithItemsResponse } from "../types/api";
import { BoardItemsList } from "../components/BoardItemsList";
import { AddItemsToBoardDialog } from "../components/AddItemsToBoardDialog";

export function BoardPage() {
  const { boardId } = useParams<{ boardId: string }>();
  const [board, setBoard] = useState<BoardWithItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  function refetch() {
    if (!boardId) return;
    getBoard(boardId)
      .then(setBoard)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load board"));
  }

  useEffect(refetch, [boardId]);

  async function handleRemove(itemId: string) {
    if (!board || !boardId) return;
    if (!window.confirm("Remove this item from the board?")) return;
    try {
      await removeItemFromBoard(boardId, itemId);
      setBoard({ ...board, items: board.items.filter((item) => item.item_id !== itemId) });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove item");
    }
  }

  const isOwner = board?.role === "owner";

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>{board?.name ?? "Board"}</h1>
        <Link to="/">Back to dashboard</Link>
      </header>

      {error && <p className="error">{error}</p>}
      {!board && !error && <p>Loading...</p>}

      {board && (
        <>
          {/* RBAC made visible, not just enforced: an owner can manage this
              board's contents; a Viewer (Decision #10) gets the identical
              list with no controls at all, not disabled ones. */}
          {!isOwner && (
            <p className="empty-state">
              Viewing as {board.role}
              {board.owner_email && <> — shared by {board.owner_email}</>}
            </p>
          )}
          {isOwner && (
            <div className="section-header">
              <span />
              <button onClick={() => setAddDialogOpen(true)}>Add Resources</button>
            </div>
          )}
          <BoardItemsList items={board.items} onRemove={isOwner ? handleRemove : undefined} />
        </>
      )}

      {addDialogOpen && board && (
        <AddItemsToBoardDialog
          boardId={board.id}
          existingItemIds={new Set(board.items.map((item) => item.item_id))}
          onClose={() => setAddDialogOpen(false)}
          onAdded={refetch}
        />
      )}
    </div>
  );
}
