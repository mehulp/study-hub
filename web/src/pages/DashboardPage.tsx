import { useAuth } from "../auth/AuthContext";

// Placeholder for now — proving the auth flow (login/signup, protected
// routing, token refresh) works end to end before building the real
// dashboard content (item fetching, tile/list views) on top of it.
export function DashboardPage() {
  const { logout } = useAuth();

  return (
    <div>
      <h1>Dashboard</h1>
      <p>You're logged in.</p>
      <button onClick={() => logout()}>Log out</button>
    </div>
  );
}
