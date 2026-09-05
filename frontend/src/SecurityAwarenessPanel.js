import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

export default function SecurityAwarenessPanel({ token }) {
  const [records, setRecords] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ user: '', title: '', due_date: '' })

  const load = () => {
    apiFetch('/training-records/', token)
      .then((data) => setRecords(unwrapList(data)))
      .catch((err) => setError(err.message))
    apiFetch('/tenant/members/', token)
      .then((data) => {
        const list = unwrapList(data)
        setMembers(list)
        if (list.length && !form.user) setForm((f) => ({ ...f, user: String(list[0].user) }))
      })
      .catch(() => setMembers([]))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const assign = (e) => {
    e.preventDefault()
    apiFetch('/training-records/', token, {
      method: 'POST',
      body: JSON.stringify({ ...form, user: Number(form.user) }),
    })
      .then(() => {
        setForm({ ...form, title: '', due_date: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const complete = (record) => {
    apiFetch(`/training-records/${record.id}/complete/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view security awareness training.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Security awareness training tracking (ISO 27001 A.6.3). Admins/auditors assign training;
        anyone can mark their own assignment complete.
      </p>

      <form onSubmit={assign} className="toolbar">
        <select value={form.user} onChange={(e) => setForm({ ...form, user: e.target.value })}>
          {members.map((m) => (
            <option key={m.id} value={m.user}>{m.username}</option>
          ))}
        </select>
        <input
          placeholder="Training title (e.g. Annual security awareness 2026)"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ width: 280 }}
          required
        />
        <input
          type="date"
          value={form.due_date}
          onChange={(e) => setForm({ ...form, due_date: e.target.value })}
        />
        <button type="submit" className="btn-primary">Assign Training</button>
        <ExportCsvButton token={token} path="/training-records/" filename="training-records.csv" />
      </form>

      {records.length === 0 ? (
        <p className="empty-state">No training records yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Trainee</th>
              <th>Title</th>
              <th>Status</th>
              <th>Due</th>
              <th>Completed</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id}>
                <td>{r.username}</td>
                <td>{r.title}</td>
                <td>
                  <StatusBadge value={r.status} />
                  {r.is_overdue && <span className="badge badge-danger" style={{ marginLeft: 6 }}>overdue</span>}
                </td>
                <td>{r.due_date || '—'}</td>
                <td>{r.completed_date || '—'}</td>
                <td>
                  {r.status !== 'completed' && (
                    <button onClick={() => complete(r)}>Mark complete</button>
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
