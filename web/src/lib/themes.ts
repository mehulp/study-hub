// Colour themes. The palettes themselves live in index.css (one [data-theme] block per theme, same
// tokens in each); this file only says which themes exist and what a saved value means.
// The inline script in index.html keeps its own copy of the ID list, because it has to run before
// React loads (so the right colours show on the very first paint, including /login and /signup).
// The two lists must stay equal (see the comment in index.html).

export type ThemeId = "sage" | "teal" | "plum" | "blue";

export const DEFAULT_THEME: ThemeId = "sage";

export const THEME_STORAGE_KEY = "study_hub.theme";

export const THEMES: { id: ThemeId; name: string; note: string }[] = [
  { id: "sage", name: "Sage & Forest", note: "Calm greens. The default." },
  { id: "teal", name: "Warm Teal", note: "Soft teal on a cool white." },
  { id: "plum", name: "Muted Plum", note: "Quiet purple, gentle contrast." },
  { id: "blue", name: "Classic Blue", note: "A clean, familiar blue." },
];

export const isValidTheme = (value: unknown): value is ThemeId =>
  typeof value === "string" && THEMES.some((theme) => theme.id === value);

// Anything at all (from storage) turned into a theme that exists.
export const resolveTheme = (value: unknown): ThemeId => (isValidTheme(value) ? value : DEFAULT_THEME);

// The saved choice, or Sage & Forest if nothing valid is saved or storage can't be read.
export function loadTheme(): ThemeId {
  try {
    return resolveTheme(localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return DEFAULT_THEME;
  }
}

// Show a theme on the page. Returns the theme actually used (an unknown value becomes the default).
export function applyTheme(value: unknown): ThemeId {
  const theme = resolveTheme(value);
  document.documentElement.setAttribute("data-theme", theme);
  return theme;
}

// Remember the choice. Returns false if the browser would not store it (the theme still applies for now).
export function saveTheme(theme: ThemeId): boolean {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    return true;
  } catch {
    return false;
  }
}
