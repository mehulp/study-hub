import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getAccessToken } from "../api/client";
import * as authApi from "../api/auth";
import type { UserResponse } from "../types/api";

interface AuthContextValue {
  isAuthenticated: boolean;
  // The display-identity source (UI redesign spec: "/me", not JWT claims)
  // -- null until the /me fetch below resolves, even while isAuthenticated
  // is already true right after login/signup.
  currentUser: UserResponse | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialized from whatever's already in storage — so a page reload
  // stays logged in rather than bouncing back to /login every time.
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAccessToken());
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    // The bridge from client.ts's clearTokens() (see its own comment) —
    // this is what lets a refresh failure deep inside some unrelated data
    // fetch actually update this component tree and trigger a redirect,
    // instead of the UI silently going stale while every request 401s.
    const handleLoggedOut = () => {
      setIsAuthenticated(false);
      setCurrentUser(null);
    };
    window.addEventListener("study_hub:logged_out", handleLoggedOut);
    return () => window.removeEventListener("study_hub:logged_out", handleLoggedOut);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    // Fires on login/signup and also on a page reload where a token
    // already existed — /me is the one place that resolves "who is this,"
    // deliberately not decoded from the JWT (Decision #73: no first_name
    // in token claims just for UI convenience).
    authApi
      .getCurrentUser()
      .then(setCurrentUser)
      .catch(() => {
        // A real auth failure here still gets handled by apiRequest's own
        // refresh-and-retry / clearTokens path; nothing extra to do.
      });
  }, [isAuthenticated]);

  async function login(email: string, password: string) {
    await authApi.login(email, password);
    setIsAuthenticated(true);
  }

  async function logout() {
    await authApi.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, currentUser, login, logout }}>
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
