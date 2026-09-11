import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getAccessToken } from "../api/client";
import * as authApi from "../api/auth";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialized from whatever's already in storage — so a page reload
  // stays logged in rather than bouncing back to /login every time.
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAccessToken());

  useEffect(() => {
    // The bridge from client.ts's clearTokens() (see its own comment) —
    // this is what lets a refresh failure deep inside some unrelated data
    // fetch actually update this component tree and trigger a redirect,
    // instead of the UI silently going stale while every request 401s.
    const handleLoggedOut = () => setIsAuthenticated(false);
    window.addEventListener("study_hub:logged_out", handleLoggedOut);
    return () => window.removeEventListener("study_hub:logged_out", handleLoggedOut);
  }, []);

  async function login(email: string, password: string) {
    await authApi.login(email, password);
    setIsAuthenticated(true);
  }

  async function logout() {
    await authApi.logout();
    setIsAuthenticated(false);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
