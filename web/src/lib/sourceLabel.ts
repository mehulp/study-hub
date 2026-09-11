// Human-readable source/domain labels, derived client-side (redesign spec
// section 18) -- no backend classification service. A resource's "source"
// here means "what site it's from," unrelated to Items' own source="manual"
// field (Decision #63).
export type ResourceKind = "video" | "article" | "link";

export interface SourceInfo {
  label: string;
  kind: ResourceKind;
}

const KNOWN_HOSTS: Record<string, SourceInfo> = {
  "youtube.com": { label: "YouTube", kind: "video" },
  "hellointerview.com": { label: "Hello Interview", kind: "article" },
  "bytebytego.com": { label: "ByteByteGo", kind: "article" },
  "excalidraw.com": { label: "Excalidraw", kind: "article" },
  "x.com": { label: "X (Twitter)", kind: "article" },
  "twitter.com": { label: "X (Twitter)", kind: "article" },
  "chatgpt.com": { label: "ChatGPT", kind: "article" },
  "claude.ai": { label: "Claude", kind: "article" },
};

export function resolveSourceInfo(url: string): SourceInfo {
  let hostname: string;
  try {
    hostname = new URL(url).hostname.replace(/^www\./, "").replace(/^app\./, "");
  } catch {
    return { label: "Link", kind: "link" };
  }

  if (KNOWN_HOSTS[hostname]) return KNOWN_HOSTS[hostname];
  if (hostname.endsWith(".github.io")) return { label: "GitHub", kind: "article" };

  // Fallback to the hostname itself, title-cased at the first segment --
  // still better than a full URL, still honest about not knowing the site.
  return { label: hostname, kind: "link" };
}
