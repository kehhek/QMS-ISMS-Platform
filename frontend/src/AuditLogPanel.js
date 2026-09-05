import React, { useEffect, useState } from 'react'
import { apiFetch, apiFetchUrl, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

export default function AuditLogPanel({ token }) {
  const [page, setPage] = useState(null)
  const [error, setError] = useState(null)

  const load = (url) => {
    const req = url ? apiFetchUrl(url, token) : apiFetch('/audit-log/', token)
    req.then(setPage).catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view the audit log.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!page) return <p className="empty-state">Loading…</p>

  const entries = unwrapList(page)

  return (
    <div>
      <p className="panel-hint">
        Visible to admin/auditor roles only. Entries are append-only — nothing here can be edited or deleted.
      </p>
      <div className="toolbar">
        <ExportCsvButton token={token} path="/audit-log/" filename="audit-log.csv" />
      </div>
      {entries.length === 0 ? (
        <p className="empty-state">No activity logged yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.created_at).toLocaleString()}</td>
                <td>{e.actor_username || 'system'}</td>
                <td><StatusBadge value={e.action} /></td>
                <td>{e.content_type_name} — {e.target_repr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="pagination">
        <button disabled={!page.previous} onClick={() => load(page.previous)}>Previous</button>
        <span>{entries.length ? `showing ${entries.length} of ${page.count}` : ''}</span>
        <button disabled={!page.next} onClick={() => load(page.next)}>Next</button>
      </div>
    </div>
  )
}
