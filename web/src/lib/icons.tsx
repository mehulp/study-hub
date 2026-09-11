// One small hand-written icon set, one consistent outline style throughout
// (redesign spec section 41 — "avoid random mixtures") — no icon library
// dependency for a handful of icons (section 7's own guidance, generalized).
interface IconProps {
  className?: string;
  size?: number;
}

function base(size = 18) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
}

export function BookIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

export function BoardsIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <rect x="3" y="3" width="7" height="18" rx="1.5" />
      <rect x="14" y="3" width="7" height="10" rx="1.5" />
    </svg>
  );
}

export function SearchIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

export function PlusIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function ChevronDownIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export function EyeIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function VideoIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <rect x="2" y="5" width="15" height="14" rx="2" />
      <path d="m17 10 5-3v10l-5-3" />
    </svg>
  );
}

export function ArticleIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M6 2h9l5 5v15H6z" />
      <path d="M15 2v5h5" />
      <path d="M9 13h6M9 17h6" />
    </svg>
  );
}

export function LinkIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.5 1.5" />
      <path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7L13 18" />
    </svg>
  );
}

export function QuoteIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M7 7h4v4c0 3-2 5-4 6l-1-2c1.5-1 2-2 2-3H7V7Z" />
      <path d="M15 7h4v4c0 3-2 5-4 6l-1-2c1.5-1 2-2 2-3h-1V7Z" />
    </svg>
  );
}

export function UserPlusIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M19 8v6M22 11h-6" />
    </svg>
  );
}

export function MenuIcon({ className, size }: IconProps) {
  return (
    <svg {...base(size)} className={className} aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}
