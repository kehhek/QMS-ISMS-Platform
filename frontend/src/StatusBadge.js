import React from 'react'

// A generic keyword -> tone mapping so every panel's status/severity
// values (drawn from several different vocabularies across Document,
// Risk, Control, Incident, Audit, CorrectiveAction, Workflow...) render
// as a consistently colored pill without each panel needing its own map.
const TONE_BY_VALUE = {
  approved: 'success', implemented: 'success', completed: 'success', closed: 'success',
  resolved: 'success', verified: 'success', active: 'success', reviewed: 'success', signed: 'success',

  in_review: 'warning', partial: 'warning', in_progress: 'warning', planned: 'warning',
  mitigating: 'warning', pending: 'warning', investigating: 'warning', contained: 'warning',
  open: 'warning', medium: 'warning', under_review: 'warning', sent: 'warning', assigned: 'warning',
  responded: 'warning',
  // CorrectiveAction's mid-workflow stages (open -> ... -> closed) — same
  // "in progress" tone as the rest of that family above.
  investigation: 'warning', action_planned: 'warning', action_implemented: 'warning',
  verification: 'warning',

  rejected: 'danger', cancelled: 'danger', not_implemented: 'danger', critical: 'danger', high: 'danger',

  draft: 'neutral', not_applicable: 'neutral', skipped: 'neutral', low: 'neutral', inactive: 'neutral',
}

// Values whose stored/DB word doesn't match the label people actually
// want to read — the underlying value stays as-is (no migration needed),
// only the displayed text changes.
const LABEL_OVERRIDE = {
  assigned: 'pending', // TrainingRecord: not yet started.
  responded: 'under review', // SupplierQuestionnaire: supplier answered, awaiting a decision.
}

export default function StatusBadge({ value }) {
  if (!value) return <span className="badge badge-neutral">—</span>
  const tone = TONE_BY_VALUE[value] || 'neutral'
  const label = LABEL_OVERRIDE[value] || value.replace(/_/g, ' ')
  return <span className={`badge badge-${tone}`}>{label}</span>
}
