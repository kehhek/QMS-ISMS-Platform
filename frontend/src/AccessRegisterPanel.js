import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '—'
}

export default function AccessRegisterPanel({ token }) {
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) return
    apiFetch('/tenant/members/', token)
      .then((data) => setMembers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view the access register.</p>
  if (error) return <p className="error-text">{error}</p>

  return (
    <div>
      <p className="panel-hint">
        Who has access to this tenant, what role they hold, and whether they're still using it —
        the standard "who can do what, and are they active" register an ISMS audit will ask for.
        Manage roles from the Members tab; this view is read-only.
      </p>
      {members.length === 0 ? (
        <p className="empty-state">No members yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Account status</th>
              <th>Access granted</th>
              <th>Account created</th>
              <th>Last login</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.username}</td>
                <td>{m.email || '—'}</td>
                <td><span className="badge badge-neutral">{m.role}</span></td>
                <td>
                  <span className={`badge ${m.is_active ? 'badge-success' : 'badge-danger'}`}>
                    {m.is_active ? 'active' : 'disabled'}
                  </span>
                </td>
                <td>{formatDate(m.created_at)}</td>
                <td>{formatDate(m.date_joined)}</td>
                <td>{formatDate(m.last_login) === '—' ? 'never' : formatDate(m.last_login)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
