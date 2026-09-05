import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

export default function MembersPanel({ token }) {
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [lastGeneratedPassword, setLastGeneratedPassword] = useState(null)
  const [form, setForm] = useState({ username: '', email: '', role: 'user' })

  const load = () => {
    apiFetch('/tenant/members/', token)
      .then((data) => setMembers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const invite = (e) => {
    e.preventDefault()
    setLastGeneratedPassword(null)
    apiFetch('/tenant/members/', token, { method: 'POST', body: JSON.stringify(form) })
      .then((data) => {
        setForm({ username: '', email: '', role: 'user' })
        setError(null)
        if (data.generated_password) setLastGeneratedPassword(`${data.username}: ${data.generated_password}`)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view members.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      {lastGeneratedPassword && (
        <p className="notice-box">
          New user created — generated password (shown once): <code>{lastGeneratedPassword}</code>
        </p>
      )}
      <p className="panel-hint">Adding a member requires the "admin" role in this tenant (or superuser).</p>
      <form onSubmit={invite} className="toolbar">
        <input
          placeholder="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
        <input
          placeholder="Email (only used if creating a new user)"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          style={{ width: 260 }}
        />
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
        >
          <option value="admin">Admin</option>
          <option value="auditor">Auditor</option>
          <option value="user">User</option>
        </select>
        <button type="submit" className="btn-primary">Add / Update Member</button>
      </form>
      {members.length === 0 ? (
        <p className="empty-state">No members yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Since</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.username}</td>
                <td>{m.email}</td>
                <td><span className="badge badge-neutral">{m.role}</span></td>
                <td>{new Date(m.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
