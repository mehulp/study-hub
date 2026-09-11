const TAG_HUE_COUNT = 8;

// Deterministic, not random or stored -- the same tag string always maps to
// the same hue index everywhere it's rendered (Study Resources rows, the
// popular-topics filter, Add-to-board's tag chips, the tag-suggestions
// dropdown), without a color column or a lookup table to keep in sync.
function tagHueIndex(tag: string): number {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = (hash * 31 + tag.charCodeAt(i)) >>> 0;
  }
  return hash % TAG_HUE_COUNT;
}

// Pastel background + saturated text, for a full chip/pill.
export function tagHueClass(tag: string): string {
  return `tag-hue-${tagHueIndex(tag)}`;
}

// Just the saturated color, as a small solid dot -- for places where a
// full colored pill would be too heavy (the tag-suggestions dropdown's
// full-width rows). Same index as tagHueClass, so a tag's dot and its pill
// elsewhere always agree.
export function tagDotClass(tag: string): string {
  return `tag-dot-${tagHueIndex(tag)}`;
}
