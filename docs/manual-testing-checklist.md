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

4. Log in as **owner** — confirm header says "Mehul's Study Hub," a small purple
   **affirmation widget** shows just below it with a proverb/affirmation (Decision #72;
   don't wait 2.5 real minutes to see it change — just confirm it's there and readable),
   **Study Resources** shows 70 items, **all rows collapsed by default** (just an arrow +
   title + tags per row — Decision #69)
5. Click a row's arrow — confirm it expands to show notes + Edit/Delete, and that clicking
   the **title itself** opens the URL in a new tab rather than toggling the row
6. Click the arrow again — confirms it collapses back
7. Tag chips: click `system-design`, `fundamentals`, `iam`, etc. — list should narrow
   correctly; click the active chip (or "All") to clear the filter
8. Scroll to **Boards I've Shared** — should show "System Design Fundamentals," 48 items,
   one grant to the receiver marked `accepted`
9. Log out, log in as **receiver** — check **Shared With Me** shows that same board with
   "— shared by mehulpatankar_owner@gmail.com" (Decision #71); click into it, confirm you
   see the 48 items as a read-only viewer (no Edit/Delete/Add/Remove buttons, "Viewing as
   viewer — shared by mehulpatankar_owner@gmail.com" label)

## Core flows, either account

10. **Add Resource**: title/URL/notes/comma-separated tags → appears in the list (collapsed
    by default) with correct tag chips
11. **Edit**: expand the new item, change title and tags → list updates immediately
12. **Delete**: remove it → confirms, disappears from the list
13. **Share**: select a few items via checkboxes (works with rows collapsed — no need to
    expand first) → "Share selected" → name a board, enter an email → copy the invite link
    shown (no real email is sent, Decision #38) → confirm it now appears under **Boards
    I've Shared** immediately, no reload needed
14. Open the invite link **in an incognito window** (so you're not still logged in as the
    sharer) → sign up or log in as whoever you invited → should land directly on the board,
    and it should now show under that account's **Shared With Me**

## Board management (owner side — Decision #70)

15. As **owner**, open the "System Design Fundamentals" board — confirm an "Add Resources"
    button is visible (owner-only) and every item row has a "Remove" button
16. Click "Add Resources" → filter by title (e.g. "LeetCode") → confirm only items **not**
    already on this board show up at all (not just disabled) → select one, "Add Selected"
    → confirm it appears in the board's item list immediately, no reload
17. Reopen "Add Resources," filter for the item you just added → confirm it's no longer
    offered (it's already on the board)
18. Click "Remove" on an item → confirm (browser confirm dialog) → confirm it disappears
    from the list immediately

## Access-control checks (the parts most worth being paranoid about)

19. As the receiver (viewer role), confirm there's genuinely no way to add/edit/delete/
    remove items on a shared board — no such buttons render at all
20. Try opening a board URL you don't have access to (grab an id from the owner's board,
    try it from an account with no grant) → should 404, not leak that the board exists
21. Log out → confirm redirected to `/login`; refresh the page while logged in → confirm
    session persists (doesn't bounce to login)

## Empty-state / edge cases

22. **Browser Bookmarks** section — should show its empty state ("No browser bookmarks
    synced yet") on every account, since the extension isn't part of this flow
23. A brand-new signup with zero data — confirm every section shows its correct empty
    state rather than erroring (Study Resources, Browser Bookmarks, Boards I've Shared,
    Shared With Me all have their own), and that **"Select all" is disabled** rather than
    clickable against zero items

## What to report back

For anything that looks wrong: which step, what you expected vs. what you saw, and if
possible whether the browser console (F12 → Console tab) shows any errors.
