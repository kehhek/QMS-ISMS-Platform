import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import ExportCsvButton from './ExportCsvButton'
import StatusBadge from './StatusBadge'

export default function NonconformancesPanel({ token }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', description: '' })
  const [reasonDrafts, setReasonDrafts] = useState({})

  const load = () => {
    apiFetch('/nonconformances/', token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const report = (e) => {
    e.preventDefault()
    apiFetch('/nonconformances/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ title: '', description: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const closeNoAction = (nc) => {
    apiFetch(`/nonconformances/${nc.id}/close_no_action/`, token, {
      method: 'POST',
      body: JSON.stringify({ closure_reason: reasonDrafts[nc.id] || '' }),
    })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  const escalate = (nc) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Escalate "${nc.title}" into a full CAPA?`)) return
    apiFetch(`/nonconformances/${nc.id}/escalate/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view nonconformances.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        A lower-barrier "something's wrong" front door than opening a CAPA directly — anyone can
        report one. Admin/auditor then triages it: close with no action needed, or escalate to a
        full corrective/preventive action.
      </p>
      <form onSubmit={report} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <input
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          style={{ width: 300 }}
        />
        <button type="submit" className="btn-primary">Report</button>
        <ExportCsvButton token={token} path="/nonconformances/" filename="nonconformances.csv" />
      </form>
      {items.length === 0 ? (
        <p className="empty-state">No nonconformances reported.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Description</th>
              <th>Status</th>
              <th>Reported By</th>
              <th>Triage</th>
            </tr>
          </thead>
          <tbody>
            {items.map((nc) => (
              <tr key={nc.id}>
                <td>{nc.title}</td>
                <td>{nc.description || '—'}</td>
                <td>
                  <StatusBadge value={nc.status} />
                  {nc.status === 'escalated' && nc.resulting_capa && (
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>CAPA #{nc.resulting_capa}</div>
                  )}
                  {nc.status === 'closed_no_action' && nc.closure_reason && (
                    <div className="cell-wrap" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{nc.closure_reason}</div>
                  )}
                </td>
                <td>{nc.reported_by_username || '—'}</td>
                <td>
                  {(nc.status === 'open' || nc.status === 'under_review') && (
                    <div className="cell-actions">
                      <input
                        placeholder="Closure reason"
                        value={reasonDrafts[nc.id] || ''}
                        onChange={(e) => setReasonDrafts({ ...reasonDrafts, [nc.id]: e.target.value })}
                        style={{ width: 120 }}
                      />
                      <button onClick={() => closeNoAction(nc)}>Close — No Action</button>
                      <button onClick={() => escalate(nc)}>Escalate to CAPA</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
