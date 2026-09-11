import { useState, type FormEvent } from "react";
import { createPlan } from "../api/plans";
import type { PlanResponse } from "../types/api";

interface CreatePlanDialogProps {
  onClose: () => void;
  onCreated: (plan: PlanResponse) => void;
}

export function CreatePlanDialog({ onClose, onCreated }: CreatePlanDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const plan = await createPlan({ name, description: description || null });
      onCreated(plan);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't create that plan. Please try again.");
      setSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-labelledby="create-plan-title">
        <h3 id="create-plan-title">New learning plan</h3>
        <form onSubmit={handleSubmit}>
          <label className="field">
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={saving}
              placeholder="System Design Interview Prep — 4 Weeks"
            />
          </label>
          <label className="field">
            Description
            <span className="dialog-hint">Optional.</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={saving}
              rows={3}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <div className="dialog-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Creating..." : "Create plan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
