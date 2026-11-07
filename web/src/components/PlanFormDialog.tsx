import { useState, type FormEvent } from "react";
import { createPlan, updatePlan } from "../api/plans";
import type { PlanResponse } from "../types/api";
import { PRACTICE_PACKS, isSupportedPack } from "../lib/interviewpalPacks";

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
  // "" = None. A saved key this version does not know is kept as it is unless the person changes it.
  const [packKey, setPackKey] = useState(plan?.interviewpal_pack_key ?? "");
  const unknownSavedKey = plan?.interviewpal_pack_key && !isSupportedPack(plan.interviewpal_pack_key) ? plan.interviewpal_pack_key : null;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const saved = isEdit
        ? await updatePlan(plan.id, { name, description: description || null, interviewpal_pack_key: packKey || null })
        : await createPlan({ name, description: description || null, interviewpal_pack_key: packKey || null });
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
          <label className="field">
            InterviewPal practice pack
            <span className="dialog-hint">Optional. A plan with a pack gets a Practise in InterviewPal button.</span>
            <select value={packKey} onChange={(e) => setPackKey(e.target.value)} disabled={saving}>
              <option value="">None</option>
              {PRACTICE_PACKS.map((pack) => (
                <option key={pack.key} value={pack.key}>
                  {pack.label}
                </option>
              ))}
              {unknownSavedKey && <option value={unknownSavedKey}>{`Unsupported pack (${unknownSavedKey}): keep`}</option>}
            </select>
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
