import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

export default function MembersPanel({ token }) {
  const [members, setMembers] = useState([])
  const [groups, setGroups] = useState([])
  const [groupFilter, setGroupFilter] = useState('')
  const [error, setError] = useState(null)
  const [lastGeneratedPassword, setLastGeneratedPassword] = useState(null)
  const [form, setForm] = useState({ username: '', email: '', role: 'user' })

  const load = () => {
    const query = groupFilter ? `?group=${groupFilter}` : ''
    apiFetch(`/tenant/members/${query}`, token)
      .then((data) => setMembers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token, groupFilter])

  useEffect(() => {
    if (!token) return
    apiFetch('/tenant/user-groups/', token).then((data) => setGroups(unwrapList(data))).catch(() => setGroups([]))
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

  const resetPassword = (member) => {
    if (!window.confirm(`Reset ${member.username}'s password? Their current password will stop working immediately.`)) return
    setLastGeneratedPassword(null)
    apiFetch(`/tenant/members/${member.id}/reset-password/`, token, { method: 'POST' })
      .then((data) => {
        setError(null)
        setLastGeneratedPassword(`${data.username}: ${data.generated_password}`)
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view members.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      {lastGeneratedPassword && (
        <p className="notice-box">
          Generated password (shown once): <code>{lastGeneratedPassword}</code>
        </p>
      )}
      <p className="panel-hint">
        Adding a member requires the "admin" role in this tenant (or superuser). Manage teams
        (Quality, Security, …) on the User Groups tab — groups are org-structure labels only, not
        a permissions boundary; role still decides what someone can do.
      </p>
      <form onSubmit={invite} className="toolbar">
        <input
          placeholder="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          required
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
      <div className="toolbar">
        <span className="field-label">Filter by group:</span>
        <select value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)}>
          <option value="">All members</option>
          {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
      </div>
      {members.length === 0 ? (
        <p className="empty-state">No members{groupFilter ? ' in this group' : ''} yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Groups</th>
              <th>Since</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.username}</td>
                <td>{m.email}</td>
                <td><span className="badge badge-neutral">{m.role}</span></td>
                <td>{m.groups && m.groups.length ? m.groups.join(', ') : '—'}</td>
                <td>{new Date(m.created_at).toLocaleDateString()}</td>
                <td>
                  <button type="button" onClick={() => resetPassword(m)}>Reset password</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
