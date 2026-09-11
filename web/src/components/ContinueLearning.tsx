import { Link } from "react-router-dom";
import type { PlanItemResponse, PlanResponse } from "../types/api";

interface ContinueLearningProps {
  plans: PlanResponse[];
}

interface PlanItemWithPlan extends PlanItemResponse {
  planId: string;
  planName: string;
}

function isThisWeek(dateStr: string): boolean {
  const target = new Date(dateStr);
  const now = new Date();
  const weekFromNow = new Date(now);
  weekFromNow.setDate(now.getDate() + 7);
  return target >= now && target <= weekFromNow;
}

function ContinueLearningRow({ item }: { item: PlanItemWithPlan }) {
  return (
    <Link to={`/plans/${item.planId}`} className="continue-learning-row">
      <span className="continue-learning-title">{item.title}</span>
      <span className="continue-learning-plan">{item.planName}</span>
    </Link>
  );
}

// "What's next," derived entirely client-side from plans already fetched
// for the Library page -- no dedicated /continue-learning endpoint
// (Decision #46/#75's rule). Renders nothing at all if the user has no
// plans yet -- PlansPage's own empty state already covers onboarding, so
// this doesn't need to repeat it.
export function ContinueLearning({ plans }: ContinueLearningProps) {
  if (plans.length === 0) return null;

  const allItems: PlanItemWithPlan[] = plans.flatMap((plan) =>
    plan.items.map((item) => ({ ...item, planId: plan.id, planName: plan.name })),
  );
  const inProgress = allItems.filter((item) => item.status === "in_progress");
  const dueThisWeek = allItems.filter(
    (item) =>
      item.status !== "completed" &&
      item.status !== "skipped" &&
      item.target_date !== null &&
      isThisWeek(item.target_date),
  );
  const activeCount = allItems.filter((item) => item.status !== "skipped").length;
  const completedCount = allItems.filter((item) => item.status === "completed").length;
  const hasAnything = inProgress.length > 0 || dueThisWeek.length > 0;

  return (
    <section className="dashboard-section">
      <h2 className="section-heading">Continue Learning</h2>
      {activeCount > 0 && (
        <p className="continue-learning-progress">
          {completedCount} of {activeCount} resources completed across your plans
        </p>
      )}
      {!hasAnything ? (
        <p className="empty-state">
          Nothing in progress right now. <Link to="/plans">Open your plans</Link> to pick something up.
        </p>
      ) : (
        <>
          {inProgress.length > 0 && (
            <div className="continue-learning-group">
              <h3 className="continue-learning-group-label">In Progress</h3>
              <div className="continue-learning-list">
                {inProgress.slice(0, 5).map((item) => (
                  <ContinueLearningRow key={item.item_id} item={item} />
                ))}
              </div>
            </div>
          )}
          {dueThisWeek.length > 0 && (
            <div className="continue-learning-group">
              <h3 className="continue-learning-group-label">Due This Week</h3>
              <div className="continue-learning-list">
                {dueThisWeek.slice(0, 5).map((item) => (
                  <ContinueLearningRow key={item.item_id} item={item} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
