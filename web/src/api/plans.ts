import { apiRequest } from "./client";
import type { PlanItemResponse, PlanItemStatus, PlanResponse, Priority } from "../types/api";

export interface CreatePlanInput {
  name: string;
  description?: string | null;
}

export async function createPlan(input: CreatePlanInput): Promise<PlanResponse> {
  return apiRequest<PlanResponse>("/items/plans", {
    method: "POST",
    body: input,
  });
}

export async function listPlans(): Promise<PlanResponse[]> {
  return apiRequest<PlanResponse[]>("/items/plans");
}

export async function getPlan(planId: string): Promise<PlanResponse> {
  return apiRequest<PlanResponse>(`/items/plans/${planId}`);
}

export interface UpdatePlanInput {
  name?: string;
  description?: string | null;
}

export async function updatePlan(planId: string, input: UpdatePlanInput): Promise<PlanResponse> {
  return apiRequest<PlanResponse>(`/items/plans/${planId}`, {
    method: "PATCH",
    body: input,
  });
}

export async function deletePlan(planId: string): Promise<void> {
  await apiRequest<void>(`/items/plans/${planId}`, { method: "DELETE" });
}

export interface AddPlanItemInput {
  item_id: string;
  status?: PlanItemStatus;
  order_index?: number | null;
  priority?: Priority | null;
  target_date?: string | null;
  estimated_effort_minutes?: number | null;
}

export async function addPlanItem(planId: string, input: AddPlanItemInput): Promise<PlanItemResponse> {
  return apiRequest<PlanItemResponse>(`/items/plans/${planId}/items`, {
    method: "POST",
    body: input,
  });
}

export interface UpdatePlanItemInput {
  status?: PlanItemStatus;
  order_index?: number | null;
  priority?: Priority | null;
  target_date?: string | null;
  estimated_effort_minutes?: number | null;
}

export async function updatePlanItem(
  planId: string,
  itemId: string,
  input: UpdatePlanItemInput,
): Promise<PlanItemResponse> {
  return apiRequest<PlanItemResponse>(`/items/plans/${planId}/items/${itemId}`, {
    method: "PATCH",
    body: input,
  });
}

export async function removePlanItem(planId: string, itemId: string): Promise<void> {
  await apiRequest<void>(`/items/plans/${planId}/items/${itemId}`, { method: "DELETE" });
}
