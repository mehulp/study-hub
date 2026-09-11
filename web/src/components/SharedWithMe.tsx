import { Link } from "react-router-dom";
import type { SharedBoardResponse } from "../types/api";

interface SharedWithMeProps {
  boards: SharedBoardResponse[];
}

// Recipient-side half of the board-visibility backlog item: before this,
// the only way back to an accepted board was re-visiting the original
// invite link (still works, invites don't expire for 7 days — Decision
// #39 — but wasn't a real answer).
export function SharedWithMe({ boards }: SharedWithMeProps) {
  if (boards.length === 0) {
    return <p className="empty-state">No boards have been shared with you yet.</p>;
  }

  return (
    <div className="board-list">
      {boards.map((board) => (
        <div key={board.id} className="board-list-row">
          <Link to={`/board/${board.id}`} className="board-list-name">
            {board.name}
          </Link>
          <span className="board-list-meta">
            {" "}
            — {board.item_count} item{board.item_count === 1 ? "" : "s"}
            {board.owner_email && <> — shared by {board.owner_email}</>}
          </span>
        </div>
      ))}
    </div>
  );
}
