import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

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

  if (!token) return <p>Set a token above to view audits.</p>

  return (
    <div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <p style={{ fontSize: 12, color: '#666' }}>
        Creating an audit requires membership in the "Auditors" or "QualityManagers" group (or superuser).
      </p>
      <form onSubmit={createAudit} style={{ marginBottom: 16 }}>
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ marginRight: 8 }}
        />
        <select
          value={form.audit_type}
          onChange={(e) => setForm({ ...form, audit_type: e.target.value })}
          style={{ marginRight: 8 }}
        >
          <option value="internal">Internal</option>
          <option value="external">External</option>
          <option value="certification">Certification</option>
        </select>
        <button type="submit">Add Audit</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
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
              <td>{a.status}</td>
              <td>{a.auditor || '—'}</td>
              <td>{a.scheduled_date || '—'}</td>
              <td>{a.completed_date || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
