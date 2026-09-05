import React, { useEffect, useState } from 'react'
import { apiFetch, apiFetchUrl, unwrapList } from './api'
import ExportCsvButton from './ExportCsvButton'

export default function SignaturesPanel({ token }) {
  const [page, setPage] = useState(null)
  const [error, setError] = useState(null)

  const load = (url) => {
    const req = url ? apiFetchUrl(url, token) : apiFetch('/signatures/', token)
    req.then(setPage).catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view signatures.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!page) return <p className="empty-state">Loading…</p>

  const entries = unwrapList(page)

  return (
    <div>
      <p className="panel-hint">
        21 CFR Part 11 electronic signatures — each one required re-entering a password at the
        moment of signing. Append-only; "Valid" confirms the record hasn't been tampered with since signing.
      </p>
      <div className="toolbar">
        <ExportCsvButton token={token} path="/signatures/" filename="signatures.csv" />
      </div>
      {entries.length === 0 ? (
        <p className="empty-state">No signatures yet — approve or reject a workflow step to create one.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Signed At</th>
              <th>Signer</th>
              <th>Meaning</th>
              <th>Record</th>
              <th>Valid</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((s) => (
              <tr key={s.id}>
                <td>{new Date(s.signed_at).toLocaleString()}</td>
                <td>{s.printed_name}</td>
                <td>{s.meaning}</td>
                <td>{s.content_type_name} — {s.target_repr}</td>
                <td>{s.valid ? '✅' : '⚠️ tampered'}</td>
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
