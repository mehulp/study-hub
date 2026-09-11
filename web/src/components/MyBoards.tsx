import { Link } from "react-router-dom";
import type { OwnedBoardResponse } from "../types/api";
import { EmptyState } from "./EmptyState";

interface MyBoardsProps {
  boards: OwnedBoardResponse[];
}

function shareStatusText(board: OwnedBoardResponse): string {
  const count = board.grants.length;
  if (count === 0) return "Not shared with anyone yet";
  return `Shared with ${count} ${count === 1 ? "person" : "people"}`;
}

// Owner-side half of the board-visibility backlog item: every board you
// own, who it's shared with, and whether they've actually accepted yet —
// "who has access to what, granted when" (SailPoint Prep, Topic 11).
// Grants show invited_email + status, same identity Board already had
// (Decision #68) -- no receiver-identity lookup added for this redesign,
// unlike the owner side (Decision #75), since nothing here needed it.
export function MyBoards({ boards }: MyBoardsProps) {
  if (boards.length === 0) {
    return (
      <EmptyState
        title="No boards yet"
        description="Select resources from your Library and share them as a board."
      />
    );
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
            <span>{shareStatusText(board)}</span>
            {board.grants.map((grant) => (
              <span
                key={grant.invited_email}
                className={grant.status === "accepted" ? "board-card-accepted" : undefined}
              >
                {grant.status === "accepted" ? "✓ " : ""}
                {grant.invited_email} {grant.status === "accepted" ? "accepted" : "(pending)"}
              </span>
            ))}
          </div>
          <span className="board-card-open">Open board →</span>
        </Link>
      ))}
    </div>
  );
}
