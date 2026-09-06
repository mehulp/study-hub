// Browser-synced items never carry a real favicon_url (the extension has no
// simple, cross-browser way to read one) — deferred to the UI, resolved
// here from the bookmark's own URL via Google's public favicon service.
export function resolveFaviconUrl(item: { url: string; favicon_url: string | null }): string {
  if (item.favicon_url) return item.favicon_url;
  try {
    const domain = new URL(item.url).hostname;
    return `https://www.google.com/s2/favicons?sz=32&domain=${domain}`;
  } catch {
    return "";
  }
}
