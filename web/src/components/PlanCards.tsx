import { Link } from "react-router-dom";
import type { PlanResponse } from "../types/api";
import { EmptyState } from "./EmptyState";

interface PlanCardsProps {
  plans: PlanResponse[];
  onCreateFirst: () => void;
}

// Same card-grid language as MyBoards.tsx -- a plan and a board are
// visually similar containers, so they should look like siblings, not two
// unrelated patterns. Progress is a pure client-side rollup over
// already-loaded item statuses (Decision #46/#75's derivation rule), not
// a separate summary endpoint.
export function PlanCards({ plans, onCreateFirst }: PlanCardsProps) {
  if (plans.length === 0) {
    return (
      <EmptyState
        title="No learning plans yet"
        description="Group resources into a sequenced plan with a status for each one — a 4-week interview-prep track, a book list, whatever you're actually working through."
        action={
          <button className="btn btn-primary" onClick={onCreateFirst}>
            + Create your first plan
          </button>
        }
      />
    );
  }

  return (
    <div className="board-cards">
      {plans.map((plan) => {
        const completed = plan.items.filter((item) => item.status === "completed").length;
        return (
          <Link key={plan.id} to={`/plans/${plan.id}`} className="board-card">
            <div className="board-card-name">{plan.name}</div>
            <div className="board-card-count">
              {plan.items.length} resource{plan.items.length === 1 ? "" : "s"}
              {plan.items.length > 0 && ` · ${completed} completed`}
            </div>
            {plan.description && <p className="plan-card-description">{plan.description}</p>}
            <span className="board-card-open">Open plan →</span>
          </Link>
        );
      })}
    </div>
  );
}
