import { useState, type FormEvent } from "react";
import { createPlan, updatePlan } from "../api/plans";
import type { PlanResponse } from "../types/api";

interface PlanFormDialogProps {
  plan?: PlanResponse; // present = edit mode, absent = create mode
  onClose: () => void;
  onSaved: (plan: PlanResponse) => void;
}

// Same dialog for create and edit (Decision #64's precedent on
// ResourceFormDialog) — `plan` being present is the only thing that
// switches which API call submit makes.
export function PlanFormDialog({ plan, onClose, onSaved }: PlanFormDialogProps) {
  const isEdit = plan !== undefined;
  const [name, setName] = useState(plan?.name ?? "");
  const [description, setDescription] = useState(plan?.description ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const saved = isEdit
        ? await updatePlan(plan.id, { name, description: description || null })
        : await createPlan({ name, description: description || null });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't save that plan. Please try again.");
      setSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-labelledby="plan-form-title">
        <h3 id="plan-form-title">{isEdit ? "Edit plan" : "New learning plan"}</h3>
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
              {saving ? "Saving..." : isEdit ? "Save changes" : "Create plan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
