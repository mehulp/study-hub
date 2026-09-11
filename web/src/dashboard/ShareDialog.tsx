import { useState, type FormEvent } from "react";
import { createBoard, addItemToBoard, createInvite } from "../api/board";

interface ShareDialogProps {
  itemIds: string[];
  onClose: () => void;
  onShared: () => void;
}

type Step = "form" | "sharing" | "done";

// No real email-sending exists yet (Decision #36/how-it-works.md) — the
// invite is a link someone has to actually hand to the recipient, so this
// dialog's whole job after creating everything is just: show that link.
export function ShareDialog({ itemIds, onClose, onShared }: ShareDialogProps) {
  const [step, setStep] = useState<Step>("form");
  const [boardName, setBoardName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setStep("sharing");
    try {
      const board = await createBoard(boardName);
      for (const itemId of itemIds) {
        await addItemToBoard(board.id, itemId);
      }
      const invite = await createInvite(board.id, email);
      // Still no real email-sending (Decision #36) — this link has to be
      // copied and handed to the recipient manually, but /invite/:token
      // is now a real page that accepts it and redirects to the board.
      setInviteLink(`${window.location.origin}/invite/${invite.invite_token}`);
      setStep("done");
      onShared();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sharing failed");
      setStep("form");
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-labelledby="share-dialog-title">
        {step !== "done" && (
          <>
            <h3 id="share-dialog-title">Share {itemIds.length} item{itemIds.length === 1 ? "" : "s"}</h3>
            <form onSubmit={handleSubmit}>
              <label className="field">
                Board name
                <input
                  value={boardName}
                  onChange={(e) => setBoardName(e.target.value)}
                  required
                  disabled={step === "sharing"}
                />
              </label>
              <label className="field">
                Recipient email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={step === "sharing"}
                />
              </label>
              {error && <p className="error">{error}</p>}
              <div className="dialog-actions">
                <button type="button" className="btn btn-secondary" onClick={onClose} disabled={step === "sharing"}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={step === "sharing"}>
                  {step === "sharing" ? "Sharing..." : "Share"}
                </button>
              </div>
            </form>
          </>
        )}
        {step === "done" && inviteLink && (
          <>
            <h3 id="share-dialog-title">Board created</h3>
            <p>
              Send this link to <strong>{email}</strong> — they'll need an account (or to
              create one) to view the board.
            </p>
            <code className="invite-token">{inviteLink}</code>
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
