import { apiRequest, clearTokens, getRefreshToken, storeTokens } from "./client";
import type { TokenResponse, UserResponse } from "../types/api";

export async function login(email: string, password: string): Promise<TokenResponse> {
  const tokens = await apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  storeTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

export async function signup(email: string, password: string): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/signup", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export async function getCurrentUser(): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/me");
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  // Best-effort: revoke the refresh token server-side (the actual point of
  // Decision #26 — a real revocation, not just forgetting the token
  // locally) — but a network failure here shouldn't block logging out
  // locally, so this deliberately doesn't propagate an error either way.
  if (refreshToken) {
    try {
      await apiRequest("/auth/logout", {
        method: "POST",
        body: { refresh_token: refreshToken },
        auth: false,
      });
    } catch {
      // ignored — clearTokens() below still runs regardless
    }
  }
  clearTokens();
}
