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
// Must match CorrectiveAction.Status in core/models.py exactly — these
// used to be a made-up ['open', 'in_progress', 'verified', 'closed'] that
// didn't match any real status, so the dropdown showed "Investigation" /
// "Action planned" / "Action implemented" / "Verification" while the
// dashboard chart silently dropped those CAPAs out of the total instead
// of counting them anywhere.
const CAPA_STAGES = ['open', 'investigation', 'action_planned', 'action_implemented', 'verification', 'closed']
const CONTROL_STAGES = ['not_implemented', 'partial', 'implemented', 'not_applicable']
const SEVERITY_STAGES = ['low', 'medium', 'high', 'critical']

function toSegments(counts, stages, colors) {
  return stages.map((stage, i) => ({
    // The raw status/severity value (e.g. "in_review") — kept alongside
    // the humanized `label` ("in review") so a click can drill into the
    // right tab pre-filtered to the exact value the backend uses.
    key: stage,
    label: stage.replace(/_/g, ' '),
    value: counts?.[stage] || 0,
    color: colors[i],
  }))
}

function sum(obj) {
  return Object.values(obj || {}).reduce((a, b) => a + b, 0)
}

export default function DashboardPanel({ token, onNavigate }) {
  // Every chart/tile below is a live drill-down, not just a picture —
  // clicking a stat tile, a stacked-bar segment, or a legend row jumps
  // to that record type's tab pre-filtered to the exact status/severity/
  // framework clicked (see ConsoleApp's pendingFilter plumbing). Falls
  // back to a no-op if this is ever rendered without onNavigate wired up.
  const goto = (tab, filter) => { if (onNavigate) onNavigate(tab, filter) }
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
  // "Open" here means "not yet closed" — every non-closed stage of the
  // real workflow, not just the literal 'open' status.
  const openCapas = Object.entries(summary.corrective_actions || {}).reduce(
    (total, [stage, count]) => (stage === 'closed' ? total : total + (count || 0)),
    0,
  )
  // Bug fix: this used to read `summary.incidents.resolved`/`.closed` —
  // but `summary.incidents` is keyed by SEVERITY (low/medium/high/
  // critical, for the "by severity" chart below), never by status, so
  // those lookups were always undefined and this always equaled the
  // full incident total regardless of any incident's real status. Use
  // the actual status breakdown instead.
  const openIncidents = summary.totals.incidents
    - (summary.incidents_by_status?.resolved || 0)
    - (summary.incidents_by_status?.closed || 0)

  const documentStagesLegend = toSegments(summary.documents, DOCUMENT_STAGES, ordinalSteps(4))
  const riskStagesLegend = toSegments(summary.risks, RISK_STAGES, ordinalSteps(3))
  const auditStagesLegend = toSegments(summary.audits, AUDIT_STAGES, ordinalSteps(4))
  const capaStagesLegend = toSegments(summary.corrective_actions, CAPA_STAGES, ordinalSteps(CAPA_STAGES.length))
  const severityLegend = toSegments(summary.incidents, SEVERITY_STAGES, SEVERITY_COLORS)
  const isoStagesLegend = toSegments(summary.controls.iso27001, CONTROL_STAGES, ordinalSteps(4))
  const soc2StagesLegend = toSegments(summary.controls.soc2, CONTROL_STAGES, ordinalSteps(4))

  return (
    <div>
      {/* Argon Dashboard's signature banner-and-overlap layout: a dark
          gradient band with the stat cards floating half on it, half
          below (negative margin on .dashboard-stat-row) — chrome only,
          the six figures themselves are unchanged from before. */}
      <div className="dashboard-header-band">
        <p className="dashboard-header-eyebrow">Overview</p>
      </div>
      <div className="stat-row dashboard-stat-row">
        <StatTile
          label="Documents" value={summary.totals.documents}
          onClick={() => goto('documents', null)} title="View all documents"
        />
        <StatTile
          label="Open risks" value={openRisks}
          onClick={() => goto('risks', null)} title="View risks"
        />
        <StatTile
          label="Open incidents" value={Math.max(openIncidents, 0)}
          onClick={() => goto('incidents', null)} title="View incidents"
        />
        <StatTile
          label="Pending approvals" value={summary.pending_approvals}
          onClick={() => goto('workflows', null)} title="View approvals"
        />
        <StatTile
          label="Open corrective actions" value={openCapas}
          onClick={() => goto('capa', null)} title="View corrective actions"
        />
        <StatTile
          label="Controls implemented" value={`${isoImplemented + soc2Implemented} / ${isoTotal + soc2Total}`}
          onClick={() => goto('controls', null)} title="View controls"
        />
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
          <StackedBar segments={documentStagesLegend} onSegmentClick={(s) => goto('documents', { status: s.key })} />
          <Legend items={documentStagesLegend} onItemClick={(s) => goto('documents', { status: s.key })} />
        </div>

        <div className="dashboard-card">
          <h4>Risks by status</h4>
          <StackedBar segments={riskStagesLegend} onSegmentClick={(s) => goto('risks', { status: s.key })} />
          <Legend items={riskStagesLegend} onItemClick={(s) => goto('risks', { status: s.key })} />
        </div>

        <div className="dashboard-card">
          <h4>Audits by status</h4>
          <StackedBar segments={auditStagesLegend} onSegmentClick={(s) => goto('audits', { status: s.key })} />
          <Legend items={auditStagesLegend} onItemClick={(s) => goto('audits', { status: s.key })} />
        </div>

        <div className="dashboard-card">
          <h4>Corrective actions by status</h4>
          <StackedBar segments={capaStagesLegend} onSegmentClick={(s) => goto('capa', { status: s.key })} />
          <Legend items={capaStagesLegend} onItemClick={(s) => goto('capa', { status: s.key })} />
        </div>

        <div className="dashboard-card">
          <h4>Incidents by severity</h4>
          <StackedBar segments={severityLegend} onSegmentClick={(s) => goto('incidents', { severity: s.key })} />
          <Legend items={severityLegend} onItemClick={(s) => goto('incidents', { severity: s.key })} />
        </div>

        <div className="dashboard-card">
          <h4>ISO 27001 controls — {isoImplemented}/{isoTotal} implemented</h4>
          <StackedBar
            segments={isoStagesLegend}
            onSegmentClick={(s) => goto('controls', { framework: 'iso27001', status: s.key })}
          />
          <Legend
            items={isoStagesLegend}
            onItemClick={(s) => goto('controls', { framework: 'iso27001', status: s.key })}
          />
        </div>

        <div className="dashboard-card">
          <h4>SOC 2 controls — {soc2Implemented}/{soc2Total} implemented</h4>
          <StackedBar
            segments={soc2StagesLegend}
            onSegmentClick={(s) => goto('controls', { framework: 'soc2', status: s.key })}
          />
          <Legend
            items={soc2StagesLegend}
            onItemClick={(s) => goto('controls', { framework: 'soc2', status: s.key })}
          />
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
