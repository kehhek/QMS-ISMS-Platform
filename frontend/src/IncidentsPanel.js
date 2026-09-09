import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import useCrudPanel from './useCrudPanel'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

const SEVERITY_OPTIONS = ['low', 'medium', 'high', 'critical']
const STATUS_OPTIONS = ['open', 'investigating', 'contained', 'resolved', 'closed']
const EMPTY_FORM = { title: '', description: '', severity: 'medium', related_risk: '' }

export default function IncidentsPanel({ token, initialFilter, onConsumeFilter }) {
  const [risks, setRisks] = useState([])
  // Seeded from a Dashboard "Incidents by severity" drill-down click.
  const [severityFilter, setSeverityFilter] = useState((initialFilter && initialFilter.severity) || '')
  const {
    items: incidents, error, form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/incidents/', token, EMPTY_FORM)

  useEffect(() => {
    if (!token) return
    apiFetch('/risks/', token).then((data) => setRisks(unwrapList(data))).catch(() => setRisks([]))
  }, [token])

  useEffect(() => {
    if (initialFilter && onConsumeFilter) onConsumeFilter()
    // Once on mount only — see severityFilter's own initializer above.
    // eslint-disable-next-line
  }, [])

  const submitCreate = (e) => {
    e.preventDefault()
    create({ ...form, related_risk: form.related_risk || null })
  }

  if (!token) return <p className="empty-state">Set a token above to view incidents.</p>

  const visibleIncidents = severityFilter ? incidents.filter((i) => i.severity === severityFilter) : incidents

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      {severityFilter && (
        <p className="panel-hint">
          Showing only <strong>{severityFilter}</strong> severity incidents —{' '}
          <button type="button" onClick={() => setSeverityFilter('')} style={{ padding: '2px 8px' }}>
            clear filter
          </button>
        </p>
      )}
      <form onSubmit={submitCreate} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
          {SEVERITY_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={form.related_risk} onChange={(e) => setForm({ ...form, related_risk: e.target.value })}>
          <option value="">No related risk</option>
          {risks.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
        <button type="submit" className="btn-primary">Report Incident</button>
        <ExportCsvButton token={token} path="/incidents/" filename="incidents.csv" />
      </form>
      {visibleIncidents.length === 0 ? (
        <p className="empty-state">{severityFilter ? 'No incidents match this filter.' : 'No incidents reported.'}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Related Risk</th>
              <th>Reported By</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleIncidents.map((i) => (
              editingId === i.id ? (
                <tr key={i.id}>
                  <td>
                    <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  </td>
                  <td>
                    <select value={editForm.severity} onChange={(e) => setEditForm({ ...editForm, severity: e.target.value })}>
                      {SEVERITY_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td>
                    <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td>
                    <select
                      value={editForm.related_risk || ''}
                      onChange={(e) => setEditForm({ ...editForm, related_risk: e.target.value || null })}
                    >
                      <option value="">No related risk</option>
                      {risks.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </td>
                  <td>{i.reported_by_username || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => saveEdit()}>Save</button>
                      <button onClick={cancelEdit}>Cancel</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={i.id}>
                  <td>{i.title}</td>
                  <td><StatusBadge value={i.severity} /></td>
                  <td><StatusBadge value={i.status} /></td>
                  <td>{risks.find((r) => r.id === i.related_risk)?.name || '—'}</td>
                  <td>{i.reported_by_username || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => startEdit(i)}>Edit</button>
                      <button onClick={() => remove(i, `"${i.title}"`)}>Delete</button>
                    </div>
                  </td>
                </tr>
              )
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
