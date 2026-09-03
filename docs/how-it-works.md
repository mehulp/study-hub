# How It Works — Plain English

Conceptual walkthroughs of what each service actually does, in plain terms — no code, no framework jargon. For *why* things are built this way, see the Decision Log in `bookmarks-hub-architecture.md`. This doc is about *what happens*, not *why we chose it*.

## Auth service

Auth is where accounts live and where you prove who you are.

- **Signing up:** you give it an email and password. It never stores your actual password — it runs it through a slow, one-way scrambling function (Argon2id) and stores only the scrambled result. Even if someone stole the database, they couldn't get your password back out of it.
- **Logging in:** you give your email and password again. Auth scrambles what you typed the same way and compares it to what's stored. If they match, you're you. In exchange, you get two things: a short-lived **access token** (good for 15 minutes) and a longer-lived **refresh token** (good for 30 days). The access token is like a wristband at a venue — show it, get in, no questions asked, but it expires fast. The refresh token is the ticket stub that lets you get a new wristband without buying a new ticket.
- **Using the access token:** any request that needs to prove who you are attaches this token. Auth signs it in a way only Auth's private key could have produced, so anyone holding Auth's *public* key (like Gateway) can check "this really came from Auth, and it hasn't expired" without ever having to ask Auth directly.
- **Refreshing:** when the 15-minute wristband expires, you hand over your refresh token to get a new wristband. Auth also swaps your old refresh token for a brand-new one every time this happens — so if someone ever steals an old, already-used refresh token and tries to use it, Auth notices that token shouldn't exist anymore and treats it as a break-in attempt: it logs you out everywhere as a precaution, not just rejecting that one request.
- **Logging out:** you hand back your refresh token and Auth marks it dead. No more wristbands can be requested with it — but your *current* wristband, if you still have an unexpired one, keeps working until it naturally expires. Logging out kills future refreshes, not an access token already in flight.

## Gateway service

Gateway is the one front door everything comes through. It doesn't store anything itself — no database, no accounts — it just decides "is this request allowed?" and hands it off to whichever real service does the actual work.

- **Once, at startup:** Gateway asks Auth "what's your public key?" and keeps it in memory for as long as it's running. That's the key it uses to tell a genuine Auth-issued token from a forged one.
- **On every request that arrives**, Gateway does the same three checks:
  1. **Where does this go?** It checks the URL against a short internal list — anything under `/auth/` goes to Auth service, `/items/` goes to Items service, `/board/` goes to Board service. No match, no forwarding — Gateway just says "not found."
  2. **Does this need a login?** A short list of things are allowed without one — signing up, logging in, refreshing, logging out. Everything else needs a valid access token attached. If it needs one and there isn't one (or it's fake/expired), Gateway rejects the request on the spot — it never even reaches the real service.
  3. **Forward it.** If it passes both checks, Gateway repackages the request — same method, same body, same token — sends it to the real service, waits for the answer, and relays that answer straight back. From the outside it looks like you talked to Auth or Items directly; you never actually did.

**Concrete example:** you call Gateway's `/auth/me` with a valid access token. Gateway sees `/me` isn't on the "no login needed" list, checks your token against the public key it fetched at startup, confirms it's real and unexpired, then quietly forwards the same request to Auth's own `/me` endpoint, gets your user info back, and hands it to you. Send a fake token instead, and Gateway catches it itself — confirmed by checking Auth's own logs and seeing that request never arrived there at all.

## Items service

Items is the catalog of every bookmark you've ever saved, from every source, in one normalized shape — the thing the dashboard actually reads from.

- **Adding a bookmark ("ingest"):** you (or eventually, a browser extension or Twitter sync job acting as you) send Items one bookmark's details — where it came from, its title, its URL, when it was saved. Items checks who you are the same way every protected endpoint does (a valid access token), then saves it under your account. If you send the *exact same* bookmark again — same source, same original ID — Items recognizes it's already there and just hands back what it already has, instead of complaining or making a duplicate. That matters because syncing is supposed to happen over and over; re-seeing something you already saved is normal, not an error.
- **Browsing your bookmarks ("list"):** ask Items for everything you've saved, optionally narrowed to just one source (just Twitter, just Chrome). It only ever shows you *your own* items — there's no way to ask for someone else's.
- **Opening one specific bookmark ("get"):** ask Items for one item by its ID. If it's yours, you get it. If it doesn't exist, or it exists but belongs to someone else, you get the exact same "not found" response either way — Items never confirms or denies that another person's bookmark exists.
- **Checking tokens itself, independently:** Items doesn't trust Gateway's word that a request is authorized — it fetches Auth's public key on its own at startup and re-checks every token itself. If Gateway somehow got bypassed, Items would still refuse a bad request on its own.

## Board service

Board is where a curated collection of bookmarks lives, ready to be shared with someone else.

- **Creating a board:** give it a name, and it makes a new board owned by you. Nothing fancy — just a name and an owner.
- **Adding an item to a board:** you point at one of your own items (by ID) and Board attaches it. Behind the scenes, Board actually asks Items "is this really this person's item?" before attaching it — using your own login token, the same way you'd ask directly — so nobody can sneak someone else's bookmark onto their board. When it attaches the item, Board also copies over the display details (title, link, little icon) right then, rather than asking Items again every time someone looks at the board later. Add the same item twice and nothing breaks — you just get back what's already there.
- **Viewing a board:** Board checks whether you're allowed to see it at all — either you own it, or you've accepted an invite to it — and if so, hands back the board's name plus every item on it, using the copies it already has. It never has to go ask Items again just to show you a board. If you have no access, or the board doesn't exist, you get the exact same "not found" either way — same reasoning as Items not confirming another person's bookmark exists.
- **Removing an item:** only the owner can do this. It's forgiving — asking to remove something that's already gone just quietly succeeds, rather than complaining.
- **Inviting someone:** the owner picks an email and Board hands back a one-time link (a random, unguessable code — there's no real email-sending in this project yet, so *something* has to carry that link to the recipient manually for now). Whoever created it stays a "viewer" — there's no picker for other roles yet.
- **Accepting an invite:** whoever is logged in and shows up with that link gets viewer access — Board doesn't check that it's specifically the person who was emailed, the same way a Google Docs "anyone with the link" share works. The first person to actually use the link is the one it sticks to, though — if someone else later gets hold of the same link, it won't work for them anymore. And accepting isn't a separate step you have to think about: the same call that accepts the invite also hands you the board right then, so you land straight on it.
- **Being a viewer:** you can see the board and everything on it, same as the owner. You cannot add or remove items, or invite anyone else — those come back as "not allowed," not silently ignored.

**Why Board keeps its own copy of the item details, instead of asking Items live every time someone looks at a board:** the original plan was for Board to call Items on the spot whenever someone views a board. But Items only ever answers "what are *your* items," scoped to whoever's asking — which works great for the owner, but breaks the moment someone else (a person the board was shared with) tries to view it, since they're not asking about their *own* items. Rather than build a whole separate way for services to vouch for each other, Board just keeps its own snapshot of what it needs to display, taken at the moment the owner added the item. The trade-off: if the original bookmark's title changed later at the source, the board's copy wouldn't know — a real cost, but a small one right now, since nothing in this project updates a bookmark after it's first saved anyway.
