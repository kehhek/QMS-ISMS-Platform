import React, { useEffect, useState } from 'react'
import { apiFetch, apiFetchUrl, unwrapList } from './api'

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

  if (!token) return <p>Set a token above to view the audit log.</p>
  if (error) return <p style={{ color: 'crimson' }}>{error}</p>
  if (!page) return <p>Loading…</p>

  const entries = unwrapList(page)

  return (
    <div>
      <p style={{ fontSize: 12, color: '#666' }}>
        Visible to admin/auditor roles only. Entries are append-only — nothing here can be edited or deleted.
      </p>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
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
              <td>{e.action}</td>
              <td>{e.content_type_name} — {e.target_repr}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 12 }}>
        <button disabled={!page.previous} onClick={() => load(page.previous)}>Previous</button>
        <span style={{ margin: '0 8px' }}>{entries.length ? `showing ${entries.length} of ${page.count}` : ''}</span>
        <button disabled={!page.next} onClick={() => load(page.next)}>Next</button>
      </div>
    </div>
  )
}
