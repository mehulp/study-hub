import type { TokenResponse } from "../types/api";

const GATEWAY_URL = "http://localhost:8000";

// Tokens live in localStorage, not memory-only state or httpOnly cookies.
// The only real alternative — httpOnly cookies set directly by Auth —
// would mean redesigning /login's response shape (Auth returns tokens in
// a JSON body today, not Set-Cookie); given that's the API actually built,
// something client-side has to hold onto them to reuse across requests
// and page reloads, and localStorage is the standard default for that.
const ACCESS_TOKEN_KEY = "study_hub_access_token";
const REFRESH_TOKEN_KEY = "study_hub_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  // apiRequest (below) can clear tokens deep inside a failed request, far
  // from any React component. AuthContext can't see a plain localStorage
  // change — React only re-renders in response to its own state changing —
  // so this event is the bridge: AuthContext listens for it and updates
  // its state, which is what lets ProtectedRoute notice and redirect.
  window.dispatchEvent(new Event("study_hub:logged_out"));
}

async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  // Same defensive pattern as the extension's shared.js (Decision #48) —
  // an error response isn't guaranteed to be JSON (Gateway's own upstream
  // failures proved that for real), so read it as text first.
  const text = await response.text();
  try {
    return JSON.parse(text).detail ?? fallback;
  } catch {
    return text ? `${fallback}: ${text}` : fallback;
  }
}

// Concurrent requests can all hit a 401 at once (e.g. the dashboard loading
// Items and Board data in parallel right as the access token expires).
// Without this, each would independently fire its own /refresh call. This
// makes every simultaneous 401 share the same in-flight refresh instead.
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    const response = await fetch(`${GATEWAY_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearTokens();
      return false;
    }
    const tokens: TokenResponse = await response.json();
    storeTokens(tokens.access_token, tokens.refresh_token);
    return true;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

interface ApiRequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean; // default true — attach the access token
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (auth) {
      const token = getAccessToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    return fetch(`${GATEWAY_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let response = await doFetch();

  // A 401 here means the access token expired mid-session (it's only good
  // for 15 minutes, Decision #25) — not necessarily "you're logged out."
  // One refresh-and-retry keeps that distinction real instead of forcing
  // a full re-login every 15 minutes.
  if (response.status === 401 && auth && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await doFetch();
    }
  }

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Request failed (${response.status})`));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}
