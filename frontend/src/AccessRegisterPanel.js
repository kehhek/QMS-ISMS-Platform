import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import ExportCsvButton from './ExportCsvButton'

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '—'
}

export default function AccessRegisterPanel({ token }) {
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [drafts, setDrafts] = useState({}) // { [membershipId]: { outcome, notes } }

  const load = () => {
    apiFetch('/tenant/members/', token)
      .then((data) => setMembers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const draftFor = (id) => drafts[id] || { outcome: 'confirmed', notes: '' }
  const setDraft = (id, changes) => setDrafts({ ...drafts, [id]: { ...draftFor(id), ...changes } })

  const submitReview = (member) => {
    const draft = draftFor(member.id)
    if (draft.outcome === 'suspended') {
      // eslint-disable-next-line no-alert
      if (!window.confirm(`Suspend ${member.username}'s account? This blocks their access immediately.`)) return
    }
    apiFetch(`/tenant/members/${member.id}/review/`, token, {
      method: 'POST',
      body: JSON.stringify(draft),
    })
      .then(() => {
        setError(null)
        setDrafts({ ...drafts, [member.id]: { outcome: 'confirmed', notes: '' } })
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view the access register.</p>
  if (error && !members.length) return <p className="error-text">{error}</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Who has access to this tenant, what role they hold, and whether they're still using it —
        plus a periodic review, so "access is reviewed regularly" (ISO 27001 A.5.18) is actual
        evidence, not just a register. Marking a review requires the admin role; suspending an
        account blocks its access immediately. Manage roles/remove members from the Members tab.
      </p>
      <div className="toolbar">
        <ExportCsvButton token={token} path="/tenant/members/" filename="access-register.csv" />
      </div>
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
              <th>Last login</th>
              <th>Last review</th>
              <th>Record a review</th>
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
                <td>{formatDate(m.last_login) === '—' ? 'never' : formatDate(m.last_login)}</td>
                <td>
                  {m.last_review ? (
                    <>
                      <span className={`badge ${m.last_review.outcome === 'suspended' ? 'badge-danger' : 'badge-success'}`}>
                        {m.last_review.outcome}
                      </span>
                      <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                        {formatDate(m.last_review.reviewed_at)} by {m.last_review.reviewed_by_username || 'system'}
                      </div>
                    </>
                  ) : (
                    <span className="badge badge-warning">never reviewed</span>
                  )}
                </td>
                <td>
                  <div className="cell-actions">
                    <select
                      value={draftFor(m.id).outcome}
                      onChange={(e) => setDraft(m.id, { outcome: e.target.value })}
                    >
                      <option value="confirmed">Confirm access</option>
                      <option value="suspended">Suspend account</option>
                    </select>
                    <input
                      placeholder="Notes"
                      value={draftFor(m.id).notes}
                      onChange={(e) => setDraft(m.id, { notes: e.target.value })}
                      style={{ width: 100 }}
                    />
                    <button onClick={() => submitReview(m)}>Record</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
