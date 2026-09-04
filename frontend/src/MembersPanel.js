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

  if (!token) return <p>Set a token above to view members.</p>

  return (
    <div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      {lastGeneratedPassword && (
        <p style={{ background: '#fffbcc', padding: 8 }}>
          New user created — generated password (shown once): <code>{lastGeneratedPassword}</code>
        </p>
      )}
      <p style={{ fontSize: 12, color: '#666' }}>
        Adding a member requires the "admin" role in this tenant (or superuser).
      </p>
      <form onSubmit={invite} style={{ marginBottom: 16 }}>
        <input
          placeholder="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          style={{ marginRight: 8 }}
        />
        <input
          placeholder="Email (only used if creating a new user)"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          style={{ marginRight: 8, width: 260 }}
        />
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
          style={{ marginRight: 8 }}
        >
          <option value="admin">Admin</option>
          <option value="auditor">Auditor</option>
          <option value="user">User</option>
        </select>
        <button type="submit">Add / Update Member</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
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
              <td>{m.role}</td>
              <td>{new Date(m.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
