import React from 'react'

// A generic keyword -> tone mapping so every panel's status/severity
// values (drawn from several different vocabularies across Document,
// Risk, Control, Incident, Audit, CorrectiveAction, Workflow...) render
// as a consistently colored pill without each panel needing its own map.
const TONE_BY_VALUE = {
  approved: 'success', implemented: 'success', completed: 'success', closed: 'success',
  resolved: 'success', verified: 'success', active: 'success', responded: 'success', reviewed: 'success',

  in_review: 'warning', partial: 'warning', in_progress: 'warning', planned: 'warning',
  mitigating: 'warning', pending: 'warning', investigating: 'warning', contained: 'warning',
  open: 'warning', medium: 'warning', under_review: 'warning', sent: 'warning',

  rejected: 'danger', cancelled: 'danger', not_implemented: 'danger', critical: 'danger', high: 'danger',

  draft: 'neutral', not_applicable: 'neutral', skipped: 'neutral', low: 'neutral', inactive: 'neutral',
}

export default function StatusBadge({ value }) {
  if (!value) return <span className="badge badge-neutral">—</span>
  const tone = TONE_BY_VALUE[value] || 'neutral'
  return <span className={`badge badge-${tone}`}>{value.replace(/_/g, ' ')}</span>
}
