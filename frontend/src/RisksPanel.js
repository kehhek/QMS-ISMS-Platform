import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'

export default function RisksPanel({ token }) {
  const [risks, setRisks] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ name: '', description: '', likelihood: 1, impact: 1 })

  const load = () => {
    apiFetch('/risks/', token)
      .then((data) => setRisks(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const createRisk = (e) => {
    e.preventDefault()
    apiFetch('/risks/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ name: '', description: '', likelihood: 1, impact: 1 })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view risks.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={createRisk} className="toolbar">
        <input
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.likelihood}
          onChange={(e) => setForm({ ...form, likelihood: Number(e.target.value) })}
          style={{ width: 60 }}
          title="Likelihood"
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.impact}
          onChange={(e) => setForm({ ...form, impact: Number(e.target.value) })}
          style={{ width: 60 }}
          title="Impact"
        />
        <button type="submit" className="btn-primary">Add Risk</button>
      </form>
      {risks.length === 0 ? (
        <p className="empty-state">No risks yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Likelihood</th>
              <th>Impact</th>
              <th>Owner</th>
              <th>Target date</th>
            </tr>
          </thead>
          <tbody>
            {risks.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td><StatusBadge value={r.status} /></td>
                <td>{r.likelihood}</td>
                <td>{r.impact}</td>
                <td>{r.owner || '—'}</td>
                <td>{r.target_date || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
