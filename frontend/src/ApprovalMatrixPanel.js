import React, { useEffect, useState } from 'react'
import { apiFetch } from './api'

const ALL_ROLES = ['admin', 'auditor', 'user']

function RoleCell({ roles }) {
  if (!Array.isArray(roles)) return <span>{String(roles)}</span>
  if (roles.length === 0) return <span className="empty-state" style={{ padding: 0 }}>none</span>
  return (
    <>
      {roles.map((r) => (
        <span
          key={r}
          className={`badge ${ALL_ROLES.includes(r) ? 'badge-neutral' : 'badge-warning'}`}
          style={{ marginRight: 4 }}
        >
          {r}
        </span>
      ))}
    </>
  )
}

export default function ApprovalMatrixPanel({ token }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) return
    apiFetch('/approval-matrix/', token).then(setRows).catch((err) => setError(err.message))
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view the approval matrix.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!rows) return <p className="empty-state">Loading…</p>

  return (
    <div>
      <p className="panel-hint">
        Which tenant roles can create/edit/delete each record type. Read directly off the API's
        own permission wiring, so this can never drift out of sync with what's actually enforced.
        Read access (viewing) is generally open to any tenant member unless noted otherwise.
      </p>
      <table>
        <thead>
          <tr>
            <th>Record type</th>
            <th>Can write (create/edit/delete)</th>
            <th>Can read</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.record_type}>
              <td>{row.record_type}</td>
              <td><RoleCell roles={row.can_write} /></td>
              <td><RoleCell roles={row.can_read} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
