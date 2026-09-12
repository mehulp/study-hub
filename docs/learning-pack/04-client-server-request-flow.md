# Study Hub — Client/Server Request Flow

*Part of the [learning pack](./). Previous: [03-data-model-and-erd.md](03-data-model-and-erd.md). Next: [05-authentication-authorization-rbac.md](05-authentication-authorization-rbac.md).*

This is "what happens when a user clicks this button" — traced exactly, not approximated.

## Login

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant A as Auth
    participant DB as Postgres

    B->>G: POST /auth/login {email, password}
    Note over G: /auth/login is a public path —<br/>no token check, forwarded as-is
    G->>A: POST /login
    A->>DB: SELECT user WHERE email = ?
    DB-->>A: password_hash
    A->>A: verify password (Argon2id)
    A->>A: sign access token (RS256, private key, 15 min)
    A->>DB: INSERT refresh_tokens row (hashed)
    A-->>G: {access_token, refresh_token}
    G-->>B: {access_token, refresh_token}
    B->>B: store both in localStorage
```

## Fetch study resources

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant I as Items
    participant DB as Postgres

    B->>G: GET /items  (Authorization: Bearer <access_token>)
    G->>G: verify JWT signature + expiry (Auth's public key, cached at startup)
    Note over G: fails fast here if invalid — never reaches Items
    G->>I: GET / (forwarded, same token)
    I->>I: independently re-verify the same JWT itself
    I->>DB: SELECT * FROM items.items WHERE owner_user_id = <from token>
    DB-->>I: rows
    I-->>G: [ItemResponse, ...]
    G-->>B: [ItemResponse, ...]
```

The re-verification in Items isn't redundant by accident — it's the point (see
[`05-authentication-authorization-rbac.md`](05-authentication-authorization-rbac.md)).

## Create/share a board

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant Bo as Board
    participant I as Items
    participant DB as Postgres

    B->>G: POST /board {name}
    G->>Bo: POST / (forwarded)
    Bo->>DB: INSERT boards row
    Bo-->>B: {id, name, ...}

    loop for each selected item
        B->>G: POST /board/{id}/items {item_id}
        G->>Bo: forwarded
        Bo->>I: GET /{item_id}  (caller's own token)
        Note over Bo,I: confirms the item is really<br/>the caller's own before attaching it
        I-->>Bo: {title, url, tags, ...}
        Bo->>DB: INSERT board_items (snapshot: title/url/tags copied now)
        Bo-->>B: 201
    end

    B->>G: POST /board/{id}/invite {invited_email}
    G->>Bo: forwarded
    Bo->>DB: INSERT access_grants (status=pending, invite_token_hash)
    Bo-->>B: {invite_token}  (shown once, for manual copy/paste — no email sent)
```

## Receiver opens the invite

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant A as Auth
    participant Bo as Board

    B->>B: open /invite/:token
    Note over B: ProtectedRoute checks isAuthenticated
    alt not logged in
        B->>B: redirect to /login, stash {from: "/invite/:token"}
        B->>G: POST /auth/login (or /auth/signup)
        G->>A: forwarded
        A-->>B: tokens
        B->>B: navigate back to the stashed /invite/:token
    end
    B->>G: POST /board/invites/{token}/accept
    G->>Bo: forwarded
    Bo->>Bo: look up access_grants by token hash
    Bo->>Bo: set user_id = caller, status = accepted
    Bo-->>B: full board + items (same response as GET /board/{id})
    B->>B: navigate straight to /board/:id — no separate "accept" screen
```

## Token refresh (a 401 mid-session)

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant A as Auth
    participant DB as Postgres

    B->>G: GET /items  (expired access_token)
    G-->>B: 401
    Note over B: client.ts catches the 401,<br/>tries one refresh-and-retry
    B->>G: POST /auth/refresh {refresh_token}
    G->>A: forwarded
    A->>DB: look up refresh_tokens by hash
    A->>A: check revoked_at IS NULL AND not expired
    A->>DB: revoke old row (revoked_at = now), INSERT new row (replaced_by_id -> old)
    A-->>B: {new access_token, new refresh_token}
    B->>B: store both, discard the old pair
    B->>G: GET /items  (retry, new access_token)
    G-->>B: 200 (the original request, now succeeding)
```

If the refresh token is *also* invalid (expired, already used once via rotation — see next
doc), this fails, the browser clears its tokens, and the user is dropped back to `/login`.

## The mechanics behind every diagram above

- **Access token**: RS256 JWT, 15-minute lifetime, carries the user's id as `sub`. Never
  looked up in a database to verify — pure signature + expiry check.
- **Refresh token**: opaque random value, 30-day lifetime, **is** looked up in a database
  (`refresh_tokens`, by its hash) on every use — this is what makes it revocable, unlike
  the access token.
- **JWT validation**: Auth signs with its private key; every other service (Gateway, Items,
  Board, Connectors) holds only the *public* key, fetched from Auth's `/.well-known/jwks.json`
  once at startup and cached in memory for the process's lifetime.
- **Gateway validation vs. backend re-verification**: Gateway's check is coarse and
  fast-failing — a bad token never reaches a backend service at all. Each backend service's
  check is the same cryptographic verification, done again, independently — not a second,
  different check, but a deliberate refusal to trust that Gateway's pass-through implies
  validity (Zero Trust in practice, not just in name).
- **Client-side token storage**: both tokens live in `localStorage`, read/written only from
  `api/client.ts` — no other file in the frontend touches storage directly.
- **The 401 refresh-and-retry flow**: exactly one retry, not a loop. If concurrent requests
  all hit a 401 at once (e.g. the Library page loading items and boards in parallel right
  as the token expires), they share a single in-flight refresh call rather than each firing
  its own — a `refreshPromise` module-level variable is memoized while a refresh is
  underway, and every caller awaits the same promise.
