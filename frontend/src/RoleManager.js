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

  if (!token) return <p>Set a token above to view roles and users.</p>

  return (
    <div>
      <h2>Groups</h2>
      <ul>
        {groups.map((g) => (
          <li key={g.id}>{g.name}</li>
        ))}
      </ul>

      <h2>Users</h2>
      <ul>
        {users.map((u) => (
          <li key={u.id}>{u.username} ({u.email})</li>
        ))}
      </ul>
    </div>
  )
}
