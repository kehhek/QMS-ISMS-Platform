import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import ExportCsvButton from './ExportCsvButton'

export default function UserGroupsPanel({ token }) {
  const [groups, setGroups] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ name: '', description: '' })
  const [addUsername, setAddUsername] = useState({}) // { [groupId]: username }

  const load = () => {
    apiFetch('/tenant/user-groups/', token)
      .then((data) => setGroups(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (!token) return
    load()
    apiFetch('/tenant/members/', token).then((data) => setMembers(unwrapList(data))).catch(() => setMembers([]))
    // eslint-disable-next-line
  }, [token])

  const create = (e) => {
    e.preventDefault()
    apiFetch('/tenant/user-groups/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ name: '', description: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const remove = (group) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete group "${group.name}"? This can't be undone — members' accounts are unaffected.`)) return
    apiFetch(`/tenant/user-groups/${group.id}/`, token, { method: 'DELETE' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  const addMember = (group) => {
    const username = addUsername[group.id]
    if (!username) return
    apiFetch(`/tenant/user-groups/${group.id}/add-member/`, token, {
      method: 'POST', body: JSON.stringify({ username }),
    })
      .then(() => {
        setAddUsername({ ...addUsername, [group.id]: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const removeMember = (group, member) => {
    apiFetch(`/tenant/user-groups/${group.id}/remove-member/`, token, {
      method: 'POST', body: JSON.stringify({ user: member.user }),
    })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view user groups.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Org-structure labels — department/team (e.g. "Quality Team", "Security Team") — not a
        permissions boundary. What someone can do is still entirely decided by their role on the
        Members tab; a group's payoff is filtering the Members list down to one team. Managing
        groups requires the admin role.
      </p>
      <form onSubmit={create} className="toolbar">
        <input
          placeholder="Group name (e.g. Quality Team)"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          placeholder="Description (optional)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          style={{ width: 240 }}
        />
        <button type="submit" className="btn-primary">Add Group</button>
        <ExportCsvButton token={token} path="/tenant/user-groups/" filename="user-groups.csv" />
      </form>
      {groups.length === 0 ? (
        <p className="empty-state">No groups yet.</p>
      ) : (
        groups.map((group) => (
          <div key={group.id} className="workflow-card">
            <div className="workflow-card-header">
              <strong>{group.name}</strong>
              <span className="badge badge-neutral">{group.member_count} member{group.member_count === 1 ? '' : 's'}</span>
              <button onClick={() => remove(group)} style={{ marginLeft: 'auto' }}>Delete Group</button>
            </div>
            {group.description && <p className="panel-hint" style={{ marginTop: -6 }}>{group.description}</p>}

            {group.members.length === 0 ? (
              <p className="empty-state">No members in this group yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Added</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {group.members.map((m) => (
                    <tr key={m.id}>
                      <td>{m.username}</td>
                      <td>{new Date(m.added_at).toLocaleDateString()}</td>
                      <td><button onClick={() => removeMember(group, m)}>Remove</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <div className="toolbar" style={{ marginTop: 10, marginBottom: 0 }}>
              <select
                value={addUsername[group.id] || ''}
                onChange={(e) => setAddUsername({ ...addUsername, [group.id]: e.target.value })}
              >
                <option value="">— pick a member —</option>
                {members
                  .filter((m) => !group.members.some((gm) => gm.user === m.user))
                  .map((m) => <option key={m.user} value={m.username}>{m.username}</option>)}
              </select>
              <button onClick={() => addMember(group)}>Add to Group</button>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
