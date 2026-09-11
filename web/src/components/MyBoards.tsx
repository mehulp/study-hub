import { Link } from "react-router-dom";
import type { OwnedBoardResponse } from "../types/api";

interface MyBoardsProps {
  boards: OwnedBoardResponse[];
}

// Owner-side half of the board-visibility backlog item: every board you
// own, who it's shared with, and whether they've actually accepted yet —
// "who has access to what, granted when" (SailPoint Prep, Topic 11).
export function MyBoards({ boards }: MyBoardsProps) {
  if (boards.length === 0) {
    return <p className="empty-state">You haven't shared any boards yet.</p>;
  }

  return (
    <div className="board-list">
      {boards.map((board) => (
        <div key={board.id} className="board-list-row">
          <div>
            <Link to={`/board/${board.id}`} className="board-list-name">
              {board.name}
            </Link>
            <span className="board-list-meta">
              {" "}
              — {board.item_count} item{board.item_count === 1 ? "" : "s"}
            </span>
          </div>
          <div className="board-list-grants">
            {board.grants.map((grant) => (
              <span key={grant.invited_email} className={`grant-badge grant-badge-${grant.status}`}>
                {grant.invited_email} ({grant.status})
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
