import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Wraps a set of routes (via React Router's nested-route + <Outlet />
// pattern) so any of them redirect to /login if not authenticated, rather
// than repeating that check in every single page component.
export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
