// Calls go through Gateway, not directly to Connectors — the extension is
// a genuine external client, same as a future web UI (Decision #47).
const GATEWAY_URL = "http://localhost:8000";

// Firefox implements the promise-based `browser` namespace natively; Chrome
// only defines `chrome`. That distinction is what `browserApi` below relies
// on (harmless either way — both objects support the same calls this file
// makes). But `typeof browser !== "undefined"` is NOT safe to also use as
// "which real browser is this" (see CONNECTION_TYPE below) — real-world
// testing found Chrome now defines a global `browser` too, which
// misidentified an actual Chrome install as Firefox and mistagged every
// synced bookmark's source. `runtime.getBrowserInfo` is the fix: a real
// WebExtensions API Firefox implements and Chrome never has, so its
// presence is a Firefox-specific signal instead of "does some object with
// this name exist."
const browserApi = typeof browser !== "undefined" ? browser : chrome;
const CONNECTION_TYPE = browserApi.runtime.getBrowserInfo ? "browser_firefox" : "browser_chrome";

async function getStoredConnection() {
  const result = await browserApi.storage.local.get(["connectionId", "pushToken"]);
  if (!result.connectionId || !result.pushToken) return null;
  return { connectionId: result.connectionId, pushToken: result.pushToken };
}

async function setStoredConnection(connectionId, pushToken) {
  await browserApi.storage.local.set({ connectionId, pushToken });
}

// A backend error response is normally JSON with a `detail` field — but
// not always: a genuine upstream failure (a timeout, a crash) can surface
// as a plain-text or HTML error page instead (this happened for real, see
// Decision #45's neighbor bug in Gateway). Reading the body as text first
// and only then attempting JSON.parse means a non-JSON error still
// produces a readable message instead of crashing on the parse itself.
async function readErrorDetail(response, fallback) {
  const text = await response.text();
  try {
    return JSON.parse(text).detail || fallback;
  } catch {
    return text ? `${fallback}: ${text}` : fallback;
  }
}

async function login(email, password) {
  const response = await fetch(`${GATEWAY_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, "Login failed"));
  }
  return response.json(); // {access_token, refresh_token, ...}
}

// The access/refresh tokens from login() are used once, right here, and
// then discarded — only the push token this returns is ever stored
// (Decision #42: a real login credential should never linger in a browser
// extension's storage).
async function createConnection(accessToken) {
  const response = await fetch(`${GATEWAY_URL}/connectors/connections`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ type: CONNECTION_TYPE }),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, "Could not create connection"));
  }
  return response.json(); // {id, type, push_token, ...}
}

async function syncBookmarks(connectionId, pushToken, items) {
  const response = await fetch(
    `${GATEWAY_URL}/connectors/connections/${connectionId}/sync`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${pushToken}`,
      },
      body: JSON.stringify({ items }),
    }
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, "Sync failed"));
  }
  return response.json(); // {results: [...]}
}
