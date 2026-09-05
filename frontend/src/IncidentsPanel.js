import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

export default function IncidentsPanel({ token }) {
  const [incidents, setIncidents] = useState([])
  const [risks, setRisks] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', description: '', severity: 'medium', related_risk: '' })

  const load = () => {
    apiFetch('/incidents/', token)
      .then((data) => setIncidents(unwrapList(data)))
      .catch((err) => setError(err.message))
    apiFetch('/risks/', token)
      .then((data) => setRisks(unwrapList(data)))
      .catch(() => setRisks([]))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const createIncident = (e) => {
    e.preventDefault()
    const payload = { ...form, related_risk: form.related_risk || null }
    apiFetch('/incidents/', token, { method: 'POST', body: JSON.stringify(payload) })
      .then(() => {
        setForm({ title: '', description: '', severity: 'medium', related_risk: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p>Set a token above to view incidents.</p>

  return (
    <div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <form onSubmit={createIncident} style={{ marginBottom: 16 }}>
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ marginRight: 8 }}
        />
        <select
          value={form.severity}
          onChange={(e) => setForm({ ...form, severity: e.target.value })}
          style={{ marginRight: 8 }}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select
          value={form.related_risk}
          onChange={(e) => setForm({ ...form, related_risk: e.target.value })}
          style={{ marginRight: 8 }}
        >
          <option value="">No related risk</option>
          {risks.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <button type="submit">Report Incident</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th>Title</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Related Risk</th>
            <th>Reported By</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((i) => (
            <tr key={i.id}>
              <td>{i.title}</td>
              <td>{i.severity}</td>
              <td>{i.status}</td>
              <td>{risks.find((r) => r.id === i.related_risk)?.name || '—'}</td>
              <td>{i.reported_by_username || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
