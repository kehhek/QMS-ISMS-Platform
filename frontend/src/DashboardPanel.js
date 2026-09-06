import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatTile from './dashboard/StatTile'
import StackedBar from './dashboard/StackedBar'
import Legend from './dashboard/Legend'
import { ordinalSteps, SEVERITY_COLORS } from './dashboard/palette'
import { EventTable } from './IsmsCalendarPanel'

// Dashboard stays a quick-glance summary, not a second ISMS Calendar —
// cap how many rows show here and point to the full tab for the rest.
// Overdue is shown in full up to this cap since "what's late" is the
// whole point of surfacing it on the dashboard at all.
const OVERDUE_CAP = 10
const UPCOMING_CAP = 5

const DOCUMENT_STAGES = ['draft', 'in_review', 'approved', 'archived']
const RISK_STAGES = ['open', 'mitigating', 'closed']
const AUDIT_STAGES = ['planned', 'in_progress', 'completed', 'cancelled']
const CAPA_STAGES = ['open', 'in_progress', 'verified', 'closed']
const CONTROL_STAGES = ['not_implemented', 'partial', 'implemented', 'not_applicable']
const SEVERITY_STAGES = ['low', 'medium', 'high', 'critical']

function toSegments(counts, stages, colors) {
  return stages.map((stage, i) => ({
    label: stage.replace(/_/g, ' '),
    value: counts?.[stage] || 0,
    color: colors[i],
  }))
}

function sum(obj) {
  return Object.values(obj || {}).reduce((a, b) => a + b, 0)
}

export default function DashboardPanel({ token }) {
  const [summary, setSummary] = useState(null)
  const [activity, setActivity] = useState(null)
  const [calendar, setCalendar] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    apiFetch('/dashboard-summary/', token)
      .then(setSummary)
      .catch((err) => setError(err.message))
    // Only admin/auditor roles can read the audit log — a plain 'user'
    // gets a 403 here, which we treat as "no feed to show", not an error.
    apiFetch('/audit-log/', token)
      .then((data) => setActivity(unwrapList(data).slice(0, 8)))
      .catch(() => setActivity(null))
    // Same overdue/upcoming aggregation the ISMS Calendar tab uses (see
    // its docstring) — any tenant member can read it, so no permission
    // fallback needed here the way the audit-log fetch above has.
    apiFetch('/isms-calendar/', token)
      .then(setCalendar)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view the dashboard.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!summary) return <p className="empty-state">Loading…</p>

  const isoTotal = sum(summary.controls.iso27001)
  const isoImplemented = summary.controls.iso27001?.implemented || 0
  const soc2Total = sum(summary.controls.soc2)
  const soc2Implemented = summary.controls.soc2?.implemented || 0

  const openRisks = (summary.risks.open || 0) + (summary.risks.mitigating || 0)
  const openCapas = (summary.corrective_actions.open || 0) + (summary.corrective_actions.in_progress || 0)
  const openIncidents = summary.totals.incidents - (summary.incidents.resolved || 0) - (summary.incidents.closed || 0)

  const documentStagesLegend = toSegments(summary.documents, DOCUMENT_STAGES, ordinalSteps(4))
  const riskStagesLegend = toSegments(summary.risks, RISK_STAGES, ordinalSteps(3))
  const auditStagesLegend = toSegments(summary.audits, AUDIT_STAGES, ordinalSteps(4))
  const capaStagesLegend = toSegments(summary.corrective_actions, CAPA_STAGES, ordinalSteps(4))
  const severityLegend = toSegments(summary.incidents, SEVERITY_STAGES, SEVERITY_COLORS)
  const isoStagesLegend = toSegments(summary.controls.iso27001, CONTROL_STAGES, ordinalSteps(4))
  const soc2StagesLegend = toSegments(summary.controls.soc2, CONTROL_STAGES, ordinalSteps(4))

  return (
    <div>
      <div className="stat-row">
        <StatTile label="Documents" value={summary.totals.documents} />
        <StatTile label="Open risks" value={openRisks} />
        <StatTile label="Open incidents" value={Math.max(openIncidents, 0)} />
        <StatTile label="Pending approvals" value={summary.pending_approvals} />
        <StatTile label="Open corrective actions" value={openCapas} />
        <StatTile label="Controls implemented" value={`${isoImplemented + soc2Implemented} / ${isoTotal + soc2Total}`} />
      </div>

      {calendar && (calendar.overdue.length > 0 || calendar.upcoming.length > 0) && (
        <div className="dashboard-grid" style={{ marginBottom: 16 }}>
          <div className="dashboard-card">
            <h4>Past due ({calendar.overdue.length})</h4>
            <EventTable events={calendar.overdue.slice(0, OVERDUE_CAP)} tone="danger" emptyLabel="Nothing overdue." />
            {calendar.overdue.length > OVERDUE_CAP && (
              <p className="panel-hint">
                +{calendar.overdue.length - OVERDUE_CAP} more — see the ISMS Calendar tab for the full list.
              </p>
            )}
          </div>

          <div className="dashboard-card">
            <h4>Upcoming ({calendar.upcoming.length})</h4>
            <EventTable events={calendar.upcoming.slice(0, UPCOMING_CAP)} tone="warning" emptyLabel="Nothing scheduled yet." />
            {calendar.upcoming.length > UPCOMING_CAP && (
              <p className="panel-hint">
                +{calendar.upcoming.length - UPCOMING_CAP} more — see the ISMS Calendar tab for the full list.
              </p>
            )}
          </div>
        </div>
      )}

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h4>Documents by stage</h4>
          <StackedBar segments={documentStagesLegend} />
          <Legend items={documentStagesLegend} />
        </div>

        <div className="dashboard-card">
          <h4>Risks by status</h4>
          <StackedBar segments={riskStagesLegend} />
          <Legend items={riskStagesLegend} />
        </div>

        <div className="dashboard-card">
          <h4>Audits by status</h4>
          <StackedBar segments={auditStagesLegend} />
          <Legend items={auditStagesLegend} />
        </div>

        <div className="dashboard-card">
          <h4>Corrective actions by status</h4>
          <StackedBar segments={capaStagesLegend} />
          <Legend items={capaStagesLegend} />
        </div>

        <div className="dashboard-card">
          <h4>Incidents by severity</h4>
          <StackedBar segments={severityLegend} />
          <Legend items={severityLegend} />
        </div>

        <div className="dashboard-card">
          <h4>ISO 27001 controls — {isoImplemented}/{isoTotal} implemented</h4>
          <StackedBar segments={isoStagesLegend} />
          <Legend items={isoStagesLegend} />
        </div>

        <div className="dashboard-card">
          <h4>SOC 2 controls — {soc2Implemented}/{soc2Total} implemented</h4>
          <StackedBar segments={soc2StagesLegend} />
          <Legend items={soc2StagesLegend} />
        </div>
      </div>

      {activity && activity.length > 0 && (
        <div className="dashboard-card" style={{ marginTop: 20 }}>
          <h4>Recent activity</h4>
          <ul className="activity-feed">
            {activity.map((a) => (
              <li key={a.id}>
                <span className="activity-time">{new Date(a.created_at).toLocaleString()}</span>
                {' — '}
                <strong>{a.actor_username || 'system'}</strong> {a.action} {a.content_type_name}
                {' '}<span className="activity-target">{a.target_repr}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
