import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'

export default function AuditsPanel({ token }) {
  const [audits, setAudits] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', scope: '', audit_type: 'internal' })

  const load = () => {
    apiFetch('/audits/', token)
      .then((data) => setAudits(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const createAudit = (e) => {
    e.preventDefault()
    apiFetch('/audits/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ title: '', scope: '', audit_type: 'internal' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view audits.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Creating an audit requires the "admin" or "auditor" role in this tenant (or superuser).
      </p>
      <form onSubmit={createAudit} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
        <select
          value={form.audit_type}
          onChange={(e) => setForm({ ...form, audit_type: e.target.value })}
        >
          <option value="internal">Internal</option>
          <option value="external">External</option>
          <option value="certification">Certification</option>
        </select>
        <button type="submit" className="btn-primary">Add Audit</button>
      </form>
      {audits.length === 0 ? (
        <p className="empty-state">No audits yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Status</th>
              <th>Auditor</th>
              <th>Scheduled</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            {audits.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td>
                <td>{a.audit_type}</td>
                <td><StatusBadge value={a.status} /></td>
                <td>{a.auditor || '—'}</td>
                <td>{a.scheduled_date || '—'}</td>
                <td>{a.completed_date || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
