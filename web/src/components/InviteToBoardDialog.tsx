import { useState, type FormEvent } from "react";
import { createInvite } from "../api/board";
import { CopyableLink } from "./CopyableLink";

interface InviteToBoardDialogProps {
  boardId: string;
  boardName: string;
  onClose: () => void;
}

type Step = "form" | "sending" | "done";

// Adds a second person to a board that already exists — distinct from
// ShareDialog, which always creates a brand-new board (Decision #9's
// still-standing part). The backend endpoint this calls (POST
// /{board_id}/invite) already existed and was already exercised by
// ShareDialog's own flow; this just exposes it as its own UI entry point
// for an owner revisiting a board they've already shared once.
export function InviteToBoardDialog({ boardId, boardName, onClose }: InviteToBoardDialogProps) {
  const [step, setStep] = useState<Step>("form");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setStep("sending");
    try {
      const invite = await createInvite(boardId, email);
      setInviteLink(`${window.location.origin}/invite/${invite.invite_token}`);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't send that invite. Please try again.");
      setStep("form");
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-labelledby="invite-dialog-title">
        {step !== "done" && (
          <>
            <h3 id="invite-dialog-title">Invite to "{boardName}"</h3>
            <form onSubmit={handleSubmit}>
              <label className="field">
                Recipient email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={step === "sending"}
                />
              </label>
              {error && <p className="error">{error}</p>}
              <div className="dialog-actions">
                <button type="button" className="btn btn-secondary" onClick={onClose} disabled={step === "sending"}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={step === "sending"}>
                  {step === "sending" ? "Sending..." : "Send invite"}
                </button>
              </div>
            </form>
          </>
        )}
        {step === "done" && inviteLink && (
          <>
            <h3 id="invite-dialog-title">Invite created</h3>
            <p>
              Send this link to <strong>{email}</strong> — they'll need an account (or to
              create one) to view the board.
            </p>
            <CopyableLink value={inviteLink} />
            <div className="dialog-actions">
              <button className="btn btn-primary" onClick={onClose}>
                Done
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
