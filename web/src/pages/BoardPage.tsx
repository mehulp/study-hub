import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getBoard } from "../api/board";
import type { BoardWithItemsResponse } from "../types/api";
import { BoardItemsList } from "../components/BoardItemsList";

export function BoardPage() {
  const { boardId } = useParams<{ boardId: string }>();
  const [board, setBoard] = useState<BoardWithItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!boardId) return;
    getBoard(boardId)
      .then(setBoard)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load board"));
  }, [boardId]);

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
          {/* Role-gated actions (remove item, invite others) are owner-only
              and not built yet — this view is read-only for every role for
              now, which is exactly correct for a Viewer (Decision #10) and
              simply incomplete, not wrong, for an owner revisiting their
              own board. */}
          {board.role !== "owner" && <p className="empty-state">Viewing as {board.role}</p>}
          <BoardItemsList items={board.items} />
        </>
      )}
    </div>
  );
}
