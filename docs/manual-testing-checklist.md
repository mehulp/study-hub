# Manual Testing Checklist

A round-trip through the app in a real browser — the part automated tests don't cover.
Update this checklist as new features are added; it's meant to be re-run, not a one-off.

## Setup

1. Confirm the stack is healthy: `docker compose ps` (all 6 services should show `healthy`)
2. Confirm the web UI is running: `curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:5173`
   (expect `200`; plain `curl http://localhost:5173` also works as a check — it just prints
   the page's HTML instead of a status code, so look for the real page markup — e.g. the
   `<title>Mehul's Study Hub</title>` line — rather than a number) — if nothing comes back,
   `bash start-dev.sh`
3. Open `http://localhost:5173` in your browser

## Fast path: the two real seeded demo accounts

These already have real data (Decision #67), so start here rather than building from
scratch:

| Account | Email | Password |
|---|---|---|
| Owner | `mehulpatankar_owner@gmail.com` | `wXOglOGoZuyuL0l9saQVyw` |
| Receiver | `mehulpatankar_receiver@gmail.com` | `jKoSJUoKtbMq2oZaXVGnHw` |

Both real demo accounts have `first_name` set (Decision #73: owner is "Mehul", receiver is
"Study Partner") — this predates the redesign, don't reset it while testing.

4. Log in as **owner** — confirm the header brand reads "Study Hub" with the tagline
   "Curate. Organize. Share what you're learning.", the page heading reads exactly
   **"Welcome back, Mehul!"** (Decision #73 personalization — not just "Welcome back"), a
   compact **affirmation widget** with a quote icon shows just below it (Decision #72;
   don't wait 2.5 real minutes to see it change — just confirm it's there and readable),
   four **stat cards** show real, non-hardcoded numbers (Study Resources = 70, Unique
   Topics, Your Boards, Browser Bookmarks), **Study Resources** shows 70 items, **all rows
   collapsed by default** (just an arrow + title + source label + tags per row —
   Decision #69)
5. Click a row's arrow — confirm it expands to show **Notes**, an **"Open resource ↗"**
   link, and Edit/Delete, and that clicking the **title itself** opens the URL in a new tab
   rather than toggling the row
6. Click the arrow again — confirms it collapses back
7. Tag chips: confirm a curated subset of ~7-9 popular tags shows by default plus a
   **"+ More"** toggle; click it — confirm a full "Search topics..." selector opens showing
   every tag with its usage count; click a tag (from either the compact row or the full
   panel) — list narrows correctly; click the active chip (or "All") to clear the filter
8. Use the **search box** ("Search resources, notes or tags...") — type a term that matches
   only a few items (e.g. a distinctive tag like `kafka`) — confirm the list narrows to
   just matching rows, and that it composes with an active tag filter rather than
   overriding it
9. Use **Sort by** — switch between "Recently added" and "Title A-Z" — confirm the order
   actually changes
10. Click **Boards** in the sidebar — should navigate to a dedicated `/boards` page (not a
    dashboard scroll section) showing **Your Boards**: "System Design Fundamentals," 48
    items, "Shared with 1 person" and the receiver's email marked `accepted`
11. Log out, log in as **receiver** — confirm the welcome heading reads
    **"Welcome back, Study Partner!"**; go to **Boards** → **Shared With Me** shows that
    same board with "Shared by Mehul" (Decision #74 — the owner's first name, not their
    email); click into it, confirm you see the 48 items as a read-only viewer: a
    **"👁 Read-only board — Shared with you by Mehul"** banner, and genuinely **no**
    Edit/Delete/Add Resources/Remove controls rendered anywhere on the page (not
    disabled — absent)

## Core flows, either account

12. **Add Resource**: click "+ Add Resource" in the header (works from any page, not just
    Library) → dialog opens with labels above each field and a "Separate tags with
    commas." hint under Tags → fill title/URL/notes/comma-separated tags → appears in the
    list (collapsed by default) with correct tag chips
13. **Edit**: expand the new item, change title and tags → list updates immediately
14. **Delete**: remove it → confirms, disappears from the list
15. **Share**: select a few items via checkboxes (works with rows collapsed — no need to
    expand first) → "Share selected" → name a board, enter an email → copy the invite link
    shown (no real email is sent, Decision #38) → confirm it now appears under **Your
    Boards** on the Boards page immediately, no reload needed
16. Open the invite link **in an incognito window** (so you're not still logged in as the
    sharer) → sign up or log in as whoever you invited → should land directly on the board,
    and it should now show under that account's **Shared With Me**
17. **"Select all" respects the active filter** (Decision #78): click a tag chip that
    narrows the list to a handful of items → "Select all" → confirm the selection count
    matches the *filtered* count, not the full library (e.g. filtering to a 3-item tag and
    clicking "Select all" should show "3 selected," not "70 selected"); clear the tag
    filter afterward and confirm the selection **persists** rather than resetting

## Signup / auth pages (Decision #73)

18. Log out, go to `/signup` — confirm a centered auth card with "Study Hub" /
    "Organize what you're learning." branding, a **required** "First name" field above
    Email and Password
19. Try submitting with First name left blank — confirm the browser's native required-field
    validation blocks it (can't submit)
20. Sign up with a real first name — confirm you land on Library with
    "Welcome back, {name}!" immediately, no reload needed
21. Log out, go to `/login` — confirm the same auth-card styling, "Welcome back" heading,
    and a "New here? Create account" link back to signup

## Board management (owner side — Decision #70)

22. As **owner**, open the "System Design Fundamentals" board — confirm a
    "You own this board" status line and an "Add Resources" button (owner-only), and every
    item row has a "Remove" button
23. Click "Add Resources" → filter by title (e.g. "LeetCode") → confirm only items **not**
    already on this board show up at all (not just disabled) → select one, "Add Selected"
    → confirm it appears in the board's item list immediately, no reload
24. Reopen "Add Resources," filter for the item you just added → confirm it's no longer
    offered (it's already on the board)
25. Click "Remove" on an item → confirm (browser confirm dialog) → confirm it disappears
    from the list immediately

## Inviting a second person to an existing board (Decision #76)

26. As **owner**, open "System Design Fundamentals" → click **"Invite"** (next to "Add
    Resources") → enter a different email → "Send invite" → confirm an invite link is
    shown (same pattern as the original Share flow)
27. Go back to the **Boards** page → confirm the board card now says
    "Shared with 2 people" and lists the new email as `(pending)` alongside the existing
    `accepted` grant
28. As the **receiver** role (viewer), confirm the "Invite" button does **not** render on
    the board page — invite stays owner-only, same as "Add Resources" and "Remove"
29. Click "Invite" again and enter the **same email** you just invited in step 26 → confirm
    a friendly inline error ("This board is already shared with that email") shows in the
    dialog, and the dialog stays open (doesn't just close on failure) — Decision #77

## Access-control checks (the parts most worth being paranoid about)

30. As the receiver (viewer role), confirm there's genuinely no way to add/edit/delete/
    remove items on a shared board — no such buttons render at all
31. Try opening a board URL you don't have access to (grab an id from the owner's board,
    try it from an account with no grant) → should show a human-readable error state, not
    leak that the board exists or show a raw stack trace
32. Log out → confirm redirected to `/login`; refresh the page while logged in → confirm
    session persists (doesn't bounce to login)

## Responsive layout

33. Resize the browser (or use devtools device emulation) to ~900px wide → confirm the
    sidebar collapses and a "☰ Menu" toggle button appears in its place; click it → sidebar
    opens inline; click again (or navigate) → it closes
34. Resize to ~400px (a phone width) → confirm no horizontal scrolling anywhere, the header
    brand text doesn't overlap the "+ Add Resource" button (it shrinks to just a "+" icon
    below ~640px), and stat cards/resource rows/dialogs all reflow to fit without clipping

## Empty-state / edge cases

35. **Browser Bookmarks** section (under "Sources / Integrations") — should show its empty
    state ("No browser bookmarks synced yet") on every account, since the extension isn't
    part of this flow
36. A brand-new signup with zero data — confirm every section shows its correct, friendly
    empty state rather than erroring (Study Resources, Browser Bookmarks, Your Boards,
    Shared With Me all have their own, e.g. "No study resources yet" with a
    "+ Add your first resource" button), and that **"Select all" is disabled** rather than
    clickable against zero items

## What to report back

For anything that looks wrong: which step, what you expected vs. what you saw, and if
possible whether the browser console (F12 → Console tab) shows any errors.
