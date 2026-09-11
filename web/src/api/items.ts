import { apiRequest } from "./client";
import type { ItemResponse } from "../types/api";

export async function listItems(): Promise<ItemResponse[]> {
  return apiRequest<ItemResponse[]>("/items");
}

export interface CreateItemInput {
  title: string;
  url: string;
  notes?: string | null;
  tags?: string[];
}

// Fills in the fields Items' ingest endpoint needs that the user shouldn't
// have to think about: source is always "manual" from this form, external_id
// is the URL itself (Decision #63 — reuses Items' own duplicate-URL
// protection for free), saved_at is just "now."
export async function createItem(input: CreateItemInput): Promise<ItemResponse> {
  return apiRequest<ItemResponse>("/items", {
    method: "POST",
    body: {
      source: "manual",
      external_id: input.url,
      title: input.title,
      url: input.url,
      notes: input.notes || null,
      tags: input.tags ?? [],
      saved_at: new Date().toISOString(),
    },
  });
}

export interface UpdateItemInput {
  title?: string;
  url?: string;
  notes?: string | null;
  tags?: string[];
}

export async function updateItem(itemId: string, input: UpdateItemInput): Promise<ItemResponse> {
  return apiRequest<ItemResponse>(`/items/${itemId}`, {
    method: "PATCH",
    body: input,
  });
}

export async function deleteItem(itemId: string): Promise<void> {
  await apiRequest<void>(`/items/${itemId}`, { method: "DELETE" });
}
