import { useEffect, useState } from "react";
import { AppLayout } from "../layout/AppLayout";
import { listMyBoards, listSharedWithMe } from "../api/board";
import type { OwnedBoardResponse, SharedBoardResponse } from "../types/api";
import { MyBoards } from "../components/MyBoards";
import { SharedWithMe } from "../components/SharedWithMe";

// Dedicated Boards destination (redesign spec section 24) -- gives sharing
// and RBAC real visual prominence instead of being two sections buried at
// the bottom of the Library page. Uses the same Board APIs Decision #68
// already built; no new aggregation endpoint.
export function BoardsPage() {
  const [myBoards, setMyBoards] = useState<OwnedBoardResponse[] | null>(null);
  const [sharedBoards, setSharedBoards] = useState<SharedBoardResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMyBoards()
      .then(setMyBoards)
      .catch(() => setError("We couldn't load your boards. Please try again."));
    listSharedWithMe()
      .then(setSharedBoards)
      .catch(() => setError("We couldn't load your boards. Please try again."));
  }, []);

  return (
    <AppLayout>
      <div className="page-heading">
        <h1>Boards</h1>
        <p>Curated selections you've shared, and boards others have shared with you.</p>
      </div>

      {error && <p className="error">{error}</p>}

      <section className="dashboard-section">
        <h2 className="section-heading">Your Boards</h2>
        {myBoards ? <MyBoards boards={myBoards} /> : <p className="loading-state">Loading boards...</p>}
      </section>

      <section className="dashboard-section">
        <h2 className="section-heading">Shared With Me</h2>
        {sharedBoards ? (
          <SharedWithMe boards={sharedBoards} />
        ) : (
          <p className="loading-state">Loading boards...</p>
        )}
      </section>
    </AppLayout>
  );
}
