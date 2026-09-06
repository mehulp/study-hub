import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Wraps a set of routes (via React Router's nested-route + <Outlet />
// pattern) so any of them redirect to /login if not authenticated, rather
// than repeating that check in every single page component. The current
// location is passed along in navigation state so LoginPage/SignupPage can
// send the user back to where they were headed (e.g. an invite link)
// instead of always landing on the dashboard.
export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Outlet />;
}
