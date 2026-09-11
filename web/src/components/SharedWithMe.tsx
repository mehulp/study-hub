import { Link } from "react-router-dom";
import type { SharedBoardResponse } from "../types/api";
import { EmptyState } from "./EmptyState";

interface SharedWithMeProps {
  boards: SharedBoardResponse[];
}

// Recipient-side half of the board-visibility backlog item: before this,
// the only way back to an accepted board was re-visiting the original
// invite link (still works, invites don't expire for 7 days — Decision
// #39 — but wasn't a real answer). Falls back to owner_email when the
// owner has no first_name (Decision #75), never silently blank.
export function SharedWithMe({ boards }: SharedWithMeProps) {
  if (boards.length === 0) {
    return <EmptyState title="Nothing has been shared with you yet." />;
  }

  return (
    <div className="board-cards">
      {boards.map((board) => (
        <Link key={board.id} to={`/board/${board.id}`} className="board-card">
          <div className="board-card-name">{board.name}</div>
          <div className="board-card-count">
            {board.item_count} resource{board.item_count === 1 ? "" : "s"}
          </div>
          <div className="board-card-share-status">
            Shared by {board.owner_first_name ?? board.owner_email ?? "someone"}
          </div>
          <span className="board-card-open">Open board →</span>
        </Link>
      ))}
    </div>
  );
}
