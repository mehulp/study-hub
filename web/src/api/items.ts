import { apiRequest } from "./client";
import type { ItemResponse } from "../types/api";

export async function listItems(): Promise<ItemResponse[]> {
  return apiRequest<ItemResponse[]>("/items");
}
