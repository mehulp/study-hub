# Known Limitations

A live-maintained list of real gaps found after the functional scope froze
(`study-hub-architecture.md`'s "Near-Term Direction" section, 2026-09-12). Separate from
that doc's own historical backlog, which is explicitly frozen and not meant to be read as
active guidance — this one is meant to be updated: never delete an entry, mark it resolved
in place with the decision number that closed it, same discipline as the Decision Log.

## Open

### Only one recipient can be invited at a time

**What happens today:** both invite flows — `ShareDialog.tsx` (create a new board and
share) and `InviteToBoardDialog.tsx` (add someone to an existing board) — take exactly one
email address per submission. `POST /{board_id}/invite`'s request body
(`InviteRequest.invited_email`) is a single `EmailStr`, not a list. Sharing with 3 people
today means 3 separate invite actions on the same board (which the app does support,
Decision #76) — not a single "invite several people at once" flow.

**What a real fix would need:** `invited_emails: list[EmailStr]` on the backend, a
batch-create over `AccessGrant` rows (each still gets its own token — an invite link is
inherently one-token-per-recipient, so this is "one submit, several grants created," not a
single shared link), and a multi-email input on the frontend (chips or comma-separated),
with each address's success/failure surfaced individually since one could already be
invited while another isn't.

**Status:** confirmed gap, deliberately not built — scope is frozen.

### No real email is sent for an invite — it's a link you copy and send yourself

**What happens today:** creating an invite (either flow) generates a real, working invite
link and shows it in the UI once — nothing gets emailed to the recipient automatically. The
owner has to copy it and send it themselves, by whatever means (Decision #38 — original
call: no transactional email provider, kept intentionally simple).

**Already designed, not built:** a full proposal for real delivery via Resend was written
in detail later — including revisiting Decision #39 (the invite link isn't checked against
the invited email at accept time; "anyone with the link" gets in, first-come-claimed) to go
with it, since real email delivery makes that trade-off worth re-examining. Explicitly
declined at the time: the existing signup-from-invite return-path flow already supports
manual sharing with zero new code, and the owner was fine sending links manually. Not a gap
found by accident — a real feature, scoped, and consciously not built.

**What a real fix would need:** an email provider integration (Resend was the one actually
evaluated — real API/pricing checked, not assumed), a transactional template, delivery
failure handling (what happens if sending fails — does invite creation still succeed?),
and very likely revisiting Decision #39 alongside it, per the reasoning above.

**Status:** confirmed gap, deliberately not built — scope is frozen.

## Resolved

### Stat cards weren't clickable, even the ones with a real destination

**What was wrong:** the Library page's "Your Boards" and "Shared With You" stat cards
showed a real, non-zero count with no way to click through to `/boards` — a number that
implies something exists with no path to go see it. This was actually a deliberate
decision at the time (#81: "kept non-clickable...for consistency across the row"), not an
oversight — revisited once it became clear two of the five cards *do* have a real nav
target and three don't, so uniform non-clickability was optimizing for the wrong thing.

**Resolved by:** Decision #95 — `StatCard` gained an optional `to` prop (renders as a
`react-router-dom` `Link` only when passed), wired to `/boards` on just the two
board-related cards.
