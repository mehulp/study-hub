import { useState } from "react";
import { THEMES, applyTheme, loadTheme, saveTheme, type ThemeId } from "../lib/themes";

// The four colour themes as swatch cards: a native radio inside a label, so keyboard (arrow keys inside the
// group) and screen readers work without extra code. Choosing one shows it at once on every screen and
// remembers it in this browser. The cards carry their own palette via data-theme-preview (see index.css).
export function ThemePicker() {
  const [current, setCurrent] = useState<ThemeId>(() => loadTheme());
  const [status, setStatus] = useState("");

  function choose(id: ThemeId) {
    const used = applyTheme(id); // shows at once, on every screen
    setCurrent(used);
    const name = THEMES.find((theme) => theme.id === used)?.name ?? used;
    setStatus(
      saveTheme(used)
        ? `${name} is on. It will be remembered in this browser.`
        : `${name} is on for now, but this browser would not store the choice, so it will not be remembered after a reload.`,
    );
  }

  return (
    <fieldset className="theme-picker">
      <legend>Colour theme</legend>
      <p className="dialog-hint">Changes every screen straight away, and is remembered in this browser.</p>
      <div className="theme-grid">
        {THEMES.map((theme) => (
          <label key={theme.id} className="theme-card" data-theme-preview={theme.id}>
            <input
              type="radio"
              name="theme"
              value={theme.id}
              checked={current === theme.id}
              onChange={() => choose(theme.id)}
            />
            <span className="theme-swatches" aria-hidden="true">
              <i className="sw-page" />
              <i className="sw-surface" />
              <i className="sw-accent" />
              <i className="sw-text" />
            </span>
            <span className="theme-name">{theme.name}</span>
            <span className="theme-note">{theme.note}</span>
            <span className="theme-selected">{"✓"} Selected</span>
          </label>
        ))}
      </div>
      <p className="theme-status" role="status" aria-live="polite">
        {status}
      </p>
    </fieldset>
  );
}
