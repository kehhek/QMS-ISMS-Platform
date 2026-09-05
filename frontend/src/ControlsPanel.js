import React, { useEffect, useState } from 'react'
import { apiFetch, apiFetchUrl, unwrapList } from './api'

const STATUS_OPTIONS = ['not_implemented', 'partial', 'implemented', 'not_applicable']

export default function ControlsPanel({ token }) {
  const [page, setPage] = useState(null) // raw paginated response
  const [framework, setFramework] = useState('')
  const [error, setError] = useState(null)

  const load = (url) => {
    const req = url
      ? apiFetchUrl(url, token)
      : apiFetch(`/controls/${framework ? `?framework=${framework}` : ''}`, token)
    req.then(setPage).catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token, framework])

  const updateControl = (control, changes) => {
    apiFetch(`/controls/${control.id}/`, token, { method: 'PATCH', body: JSON.stringify(changes) })
      .then((updated) => {
        setPage({
          ...page,
          results: page.results.map((c) => (c.id === updated.id ? updated : c)),
        })
        setError(null)
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view controls.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!page) return <p className="empty-state">Loading…</p>

  const controls = unwrapList(page)

  return (
    <div>
      <div className="toolbar">
        <span className="field-label">Framework:</span>
        <select value={framework} onChange={(e) => setFramework(e.target.value)}>
          <option value="">All ({page.count})</option>
          <option value="iso27001">ISO 27001</option>
          <option value="soc2">SOC 2</option>
        </select>
      </div>
      <table>
        <thead>
          <tr>
            <th>Framework</th>
            <th>ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Owner</th>
          </tr>
        </thead>
        <tbody>
          {controls.map((c) => (
            <tr key={c.id}>
              <td><span className="badge badge-neutral">{c.framework}</span></td>
              <td>{c.identifier}</td>
              <td>{c.name}</td>
              <td>
                <select value={c.status} onChange={(e) => updateControl(c, { status: e.target.value })}>
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  defaultValue={c.owner}
                  onBlur={(e) => {
                    if (e.target.value !== c.owner) updateControl(c, { owner: e.target.value })
                  }}
                  style={{ width: 120 }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pagination">
        <button disabled={!page.previous} onClick={() => load(page.previous)}>Previous</button>
        <span>{controls.length ? `showing ${controls.length} of ${page.count}` : ''}</span>
        <button disabled={!page.next} onClick={() => load(page.next)}>Next</button>
      </div>
    </div>
  )
}
