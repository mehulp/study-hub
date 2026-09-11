import { apiRequest } from "./client";
import type { ItemResponse } from "../types/api";

export async function listItems(): Promise<ItemResponse[]> {
  return apiRequest<ItemResponse[]>("/items");
}

export interface CreateItemInput {
  title: string;
  url: string;
  notes?: string | null;
  imageUrl?: string | null;
  tags?: string[];
}

// Fills in the fields Items' ingest endpoint needs that the user shouldn't
// have to think about: source is always "manual" from this form, external_id
// is the URL itself (Decision #63 — reuses Items' own duplicate-URL
// protection for free), saved_at is just "now." `imageUrl` maps onto the
// same `preview_media_url` column connectors already populate (Decision
// #84) — manual entry just wasn't wired to set it before.
export async function createItem(input: CreateItemInput): Promise<ItemResponse> {
  return apiRequest<ItemResponse>("/items", {
    method: "POST",
    body: {
      source: "manual",
      external_id: input.url,
      title: input.title,
      url: input.url,
      notes: input.notes || null,
      preview_media_url: input.imageUrl || null,
      tags: input.tags ?? [],
      saved_at: new Date().toISOString(),
    },
  });
}

export interface UpdateItemInput {
  title?: string;
  url?: string;
  notes?: string | null;
  imageUrl?: string | null;
  tags?: string[];
}

export async function updateItem(itemId: string, input: UpdateItemInput): Promise<ItemResponse> {
  // Rename imageUrl -> preview_media_url only when the caller actually
  // included it (even as null, to clear it) -- the backend's PATCH handler
  // distinguishes "field absent" (leave unchanged) from "field present"
  // (apply as given, Decision #64's model_fields_set pattern), so a key
  // that's merely undefined here must not be sent at all.
  const { imageUrl, ...rest } = input;
  const body: Record<string, unknown> = { ...rest };
  if ("imageUrl" in input) {
    body.preview_media_url = imageUrl;
  }
  return apiRequest<ItemResponse>(`/items/${itemId}`, {
    method: "PATCH",
    body,
  });
}

export async function deleteItem(itemId: string): Promise<void> {
  await apiRequest<void>(`/items/${itemId}`, { method: "DELETE" });
}
