import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getPlan, updatePlanItem, removePlanItem, deletePlan } from "../api/plans";
import type { PlanResponse, PlanItemStatus, Priority } from "../types/api";
import { AppLayout } from "../layout/AppLayout";
import { PlanItemsList } from "../components/PlanItemsList";
import { AddItemsToPlanDialog } from "../components/AddItemsToPlanDialog";
import { PlusIcon } from "../lib/icons";

export function PlanDetailPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  function refetch() {
    if (!planId) return;
    getPlan(planId)
      .then(setPlan)
      .catch(() => setError("We couldn't load this plan. Please try again."));
  }

  useEffect(refetch, [planId]);

  async function handleStatusChange(itemId: string, status: PlanItemStatus) {
    if (!plan) return;
    try {
      const updated = await updatePlanItem(plan.id, itemId, { status });
      setPlan({
        ...plan,
        items: plan.items.map((item) => (item.item_id === itemId ? updated : item)),
      });
    } catch {
      setError("We couldn't update that item. Please try again.");
    }
  }

  async function handlePriorityChange(itemId: string, priority: Priority | null) {
    if (!plan) return;
    try {
      const updated = await updatePlanItem(plan.id, itemId, { priority });
      setPlan({
        ...plan,
        items: plan.items.map((item) => (item.item_id === itemId ? updated : item)),
      });
    } catch {
      setError("We couldn't update that item. Please try again.");
    }
  }

  async function handleTargetDateChange(itemId: string, targetDate: string | null) {
    if (!plan) return;
    try {
      const updated = await updatePlanItem(plan.id, itemId, { target_date: targetDate });
      setPlan({
        ...plan,
        items: plan.items.map((item) => (item.item_id === itemId ? updated : item)),
      });
    } catch {
      setError("We couldn't update that item. Please try again.");
    }
  }

  async function handleRemove(itemId: string) {
    if (!plan) return;
    if (!window.confirm("Remove this resource from the plan?")) return;
    try {
      await removePlanItem(plan.id, itemId);
      setPlan({ ...plan, items: plan.items.filter((item) => item.item_id !== itemId) });
    } catch {
      setError("We couldn't remove that item. Please try again.");
    }
  }

  async function handleDeletePlan() {
    if (!plan) return;
    if (!window.confirm(`Delete "${plan.name}"? This can't be undone.`)) return;
    try {
      await deletePlan(plan.id);
      navigate("/plans");
    } catch {
      setError("We couldn't delete this plan. Please try again.");
    }
  }

  const completedCount = plan?.items.filter((item) => item.status === "completed").length ?? 0;

  return (
    <AppLayout>
      <Link to="/plans" className="board-page-back">
        ‹ Plans
      </Link>

      {error && <p className="error">{error}</p>}
      {!plan && !error && <p className="loading-state">Loading plan...</p>}

      {plan && (
        <>
          <div className="page-heading">
            <h1>{plan.name}</h1>
            <p>
              {plan.items.length} resource{plan.items.length === 1 ? "" : "s"}
              {plan.items.length > 0 && ` · ${completedCount} completed`}
            </p>
            {plan.description && <p className="plan-description">{plan.description}</p>}
          </div>

          <div className="section-header">
            <span />
            <div className="board-page-actions">
              <button className="btn btn-secondary" onClick={() => setAddDialogOpen(true)}>
                <PlusIcon size={16} />
                Add Resources
              </button>
              <button className="btn btn-danger" onClick={handleDeletePlan}>
                Delete Plan
              </button>
            </div>
          </div>

          <PlanItemsList
            items={plan.items}
            onStatusChange={handleStatusChange}
            onPriorityChange={handlePriorityChange}
            onTargetDateChange={handleTargetDateChange}
            onRemove={handleRemove}
          />
        </>
      )}

      {addDialogOpen && plan && (
        <AddItemsToPlanDialog
          planId={plan.id}
          planName={plan.name}
          existingItemIds={new Set(plan.items.map((item) => item.item_id))}
          onClose={() => setAddDialogOpen(false)}
          onAdded={refetch}
        />
      )}
    </AppLayout>
  );
}
