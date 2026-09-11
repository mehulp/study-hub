import { useEffect, useState } from "react";
import { AppLayout } from "../layout/AppLayout";
import { listPlans } from "../api/plans";
import type { PlanResponse } from "../types/api";
import { PlanCards } from "../components/PlanCards";
import { CreatePlanDialog } from "../components/CreatePlanDialog";
import { PlusIcon } from "../lib/icons";

// Dedicated Plans destination (roadmap Phase 1, Decision #85) -- same
// "give it real visual prominence, not a buried section" reasoning as
// BoardsPage (redesign spec section 24).
export function PlansPage() {
  const [plans, setPlans] = useState<PlanResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    listPlans()
      .then(setPlans)
      .catch(() => setError("We couldn't load your plans. Please try again."));
  }, []);

  return (
    <AppLayout>
      <div className="section-header">
        <div className="page-heading">
          <h1>Plans</h1>
          <p>Sequenced study plans, with a status for each resource.</p>
        </div>
        {plans && plans.length > 0 && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <PlusIcon size={16} />
            New Plan
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      {!plans && !error && <p className="loading-state">Loading plans...</p>}

      {plans && (
        <PlanCards plans={plans} onCreateFirst={() => setCreateOpen(true)} />
      )}

      {createOpen && (
        <CreatePlanDialog
          onClose={() => setCreateOpen(false)}
          onCreated={(plan) => setPlans((current) => [plan, ...(current ?? [])])}
        />
      )}
    </AppLayout>
  );
}
