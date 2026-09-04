import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

export default function CorrectiveActionsPanel({ token }) {
  const [actions, setActions] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', description: '', action_type: 'corrective' })

  const load = () => {
    apiFetch('/corrective-actions/', token)
      .then((data) => setActions(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
  }, [token])

  const createAction = (e) => {
    e.preventDefault()
    apiFetch('/corrective-actions/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ title: '', description: '', action_type: 'corrective' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p>Set a token above to view corrective actions.</p>

  return (
    <div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <form onSubmit={createAction} style={{ marginBottom: 16 }}>
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ marginRight: 8 }}
        />
        <select
          value={form.action_type}
          onChange={(e) => setForm({ ...form, action_type: e.target.value })}
          style={{ marginRight: 8 }}
        >
          <option value="corrective">Corrective</option>
          <option value="preventive">Preventive</option>
        </select>
        <button type="submit">Add CAPA</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th>Title</th>
            <th>Type</th>
            <th>Status</th>
            <th>Owner</th>
            <th>Audit</th>
            <th>Risk</th>
            <th>Due</th>
          </tr>
        </thead>
        <tbody>
          {actions.map((a) => (
            <tr key={a.id}>
              <td>{a.title}</td>
              <td>{a.action_type}</td>
              <td>{a.status}</td>
              <td>{a.owner || '—'}</td>
              <td>{a.audit ?? '—'}</td>
              <td>{a.risk ?? '—'}</td>
              <td>{a.due_date || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
