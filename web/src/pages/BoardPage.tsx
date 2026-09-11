import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getBoard, removeItemFromBoard } from "../api/board";
import type { BoardWithItemsResponse } from "../types/api";
import { AppLayout } from "../layout/AppLayout";
import { BoardItemsList } from "../components/BoardItemsList";
import { AddItemsToBoardDialog } from "../components/AddItemsToBoardDialog";
import { InviteToBoardDialog } from "../components/InviteToBoardDialog";
import { EyeIcon, PlusIcon, UserPlusIcon } from "../lib/icons";

export function BoardPage() {
  const { boardId } = useParams<{ boardId: string }>();
  const [board, setBoard] = useState<BoardWithItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);

  function refetch() {
    if (!boardId) return;
    getBoard(boardId)
      .then(setBoard)
      .catch(() => setError("We couldn't load this board. Please try again."));
  }

  useEffect(refetch, [boardId]);

  async function handleRemove(itemId: string) {
    if (!board || !boardId) return;
    if (!window.confirm("Remove this item from the board?")) return;
    try {
      await removeItemFromBoard(boardId, itemId);
      setBoard({ ...board, items: board.items.filter((item) => item.item_id !== itemId) });
    } catch {
      setError("We couldn't remove that item. Please try again.");
    }
  }

  const isOwner = board?.role === "owner";

  return (
    <AppLayout>
      <Link to="/boards" className="board-page-back">
        ‹ Boards
      </Link>

      {error && <p className="error">{error}</p>}
      {!board && !error && <p className="loading-state">Loading board...</p>}

      {board && (
        <>
          <div className="page-heading">
            <h1>{board.name}</h1>
            <p>
              {board.items.length} resource{board.items.length === 1 ? "" : "s"}
            </p>
          </div>

          {/* RBAC made visible, not just enforced: an owner can manage this
              board's contents; a Viewer (Decision #10) sees a read-only
              banner and never sees a mutation control rendered at all, not
              a disabled one. */}
          {isOwner ? (
            <div className="board-status-banner owner">You own this board</div>
          ) : (
            <div className="board-status-banner">
              <EyeIcon size={16} />
              Read-only board — Shared with you by{" "}
              {board.owner_first_name ?? board.owner_email ?? "the owner"}
            </div>
          )}

          {isOwner && (
            <div className="section-header">
              <span />
              <div className="board-page-actions">
                <button className="btn btn-secondary" onClick={() => setInviteDialogOpen(true)}>
                  <UserPlusIcon size={16} />
                  Invite
                </button>
                <button className="btn btn-secondary" onClick={() => setAddDialogOpen(true)}>
                  <PlusIcon size={16} />
                  Add Resources
                </button>
              </div>
            </div>
          )}

          <BoardItemsList items={board.items} onRemove={isOwner ? handleRemove : undefined} />
        </>
      )}

      {addDialogOpen && board && (
        <AddItemsToBoardDialog
          boardId={board.id}
          boardName={board.name}
          existingItemIds={new Set(board.items.map((item) => item.item_id))}
          onClose={() => setAddDialogOpen(false)}
          onAdded={refetch}
        />
      )}

      {inviteDialogOpen && board && (
        <InviteToBoardDialog
          boardId={board.id}
          boardName={board.name}
          onClose={() => setInviteDialogOpen(false)}
        />
      )}
    </AppLayout>
  );
}
