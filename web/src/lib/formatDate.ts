// Readable, never raw ISO (redesign spec section 40) -- only used where a
// real timestamp already exists (Items' saved_at), never a fabricated one.
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
