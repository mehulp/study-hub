import { useState } from "react";
import { CheckIcon, CopyIcon } from "../lib/icons";

interface CopyableLinkProps {
  value: string;
}

// Shared by ShareDialog and InviteToBoardDialog -- both show a freshly
// created invite link with nothing to send it anywhere (Decision #38, no
// real email-sending), so copying it by hand is the only path a user has.
// Selecting the raw <code> text worked before but wasn't obvious; this adds
// a one-click copy with brief "Copied" feedback.
export function CopyableLink({ value }: CopyableLinkProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API can be unavailable (e.g. no permission) -- the link
      // text underneath is still selectable and copyable by hand either way.
    }
  }

  return (
    <div className="copyable-link">
      <code className="invite-token">{value}</code>
      <button type="button" className="btn btn-secondary btn-sm copy-link-btn" onClick={handleCopy}>
        {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}
