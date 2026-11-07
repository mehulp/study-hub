import { useEffect, useRef } from "react";
import { ThemePicker } from "./ThemePicker";

interface AppearanceDialogProps {
  onClose: () => void;
}

// "Appearance" from the avatar menu. Same dialog look as the other dialogs, plus what a keyboard user needs:
// focus moves into it when it opens (to the selected theme), Tab stays inside it, and Escape closes it. The
// caller puts focus back on the avatar button when it closes.
export function AppearanceDialog({ onClose }: AppearanceDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    const selected = dialog?.querySelector<HTMLInputElement>("input[type=radio]:checked");
    (selected ?? dialog?.querySelector<HTMLElement>("input,button"))?.focus();
  }, []);

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab" || !dialogRef.current) return;
    const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>("input:not([disabled]),button:not([disabled])")];
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="dialog-backdrop">
      <div
        className="dialog dialog-appearance"
        role="dialog"
        aria-modal="true"
        aria-labelledby="appearance-title"
        ref={dialogRef}
        onKeyDown={handleKeyDown}
      >
        <h3 id="appearance-title">Appearance</h3>
        <ThemePicker />
        <div className="dialog-actions">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
