import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { acceptInvite } from "../api/board";

// By the time this renders, ProtectedRoute has already guaranteed the
// visitor is logged in (bouncing them through /login and back via the
// `from` state if not) — so this page's only job is: accept, then redirect
// straight to the board. Nothing here asks the user to do anything, per
// Journey 4's "no separate accept invite step."
export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  // Effects can double-fire in React's StrictMode dev checks — harmless
  // for a read, but accept_invite has a real side effect (claims the
  // grant), so this guards against calling it twice.
  const requested = useRef(false);

  useEffect(() => {
    if (!token || requested.current) return;
    requested.current = true;
    acceptInvite(token)
      .then((board) => navigate(`/board/${board.id}`, { replace: true }))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not accept invite"));
  }, [token, navigate]);

  return (
    <div className="dashboard">
      {error ? <p className="error">{error}</p> : <p>Accepting invite...</p>}
    </div>
  );
}
