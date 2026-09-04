import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  if (!token) return <p>Set a token above to view risks.</p>

  return (
    <div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <form onSubmit={createRisk} style={{ marginBottom: 16 }}>
        <input
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          style={{ marginRight: 8 }}
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.likelihood}
          onChange={(e) => setForm({ ...form, likelihood: Number(e.target.value) })}
          style={{ width: 60, marginRight: 8 }}
          title="Likelihood"
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.impact}
          onChange={(e) => setForm({ ...form, impact: Number(e.target.value) })}
          style={{ width: 60, marginRight: 8 }}
          title="Impact"
        />
        <button type="submit">Add Risk</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
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
              <td>{r.status}</td>
              <td>{r.likelihood}</td>
              <td>{r.impact}</td>
              <td>{r.owner || '—'}</td>
              <td>{r.target_date || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
