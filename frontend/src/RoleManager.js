import React, { useState, useEffect } from 'react'
import { apiFetch, unwrapList } from './api'

export default function RoleManager({ token }) {
  const [groups, setGroups] = useState([])
  const [users, setUsers] = useState([])

  useEffect(() => {
    if (!token) return

    apiFetch('/accounts/groups/', token)
      .then((data) => setGroups(unwrapList(data)))
      .catch(() => setGroups([]))

    apiFetch('/accounts/users/', token)
      .then((data) => setUsers(unwrapList(data)))
      .catch(() => setUsers([]))
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view roles and users.</p>

  return (
    <div style={{ display: 'flex', gap: 40 }}>
      <div>
        <h3>Groups</h3>
        {groups.length === 0 ? (
          <p className="empty-state">None</p>
        ) : (
          <ul>
            {groups.map((g) => (
              <li key={g.id}>{g.name}</li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3>Users</h3>
        {users.length === 0 ? (
          <p className="empty-state">None</p>
        ) : (
          <ul>
            {users.map((u) => (
              <li key={u.id}>{u.username} ({u.email})</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
